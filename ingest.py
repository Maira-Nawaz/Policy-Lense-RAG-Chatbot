"""
PolicyLens ingestion pipeline.

For every document in corpus/manifest.json:
  1. Validate the manifest entry.
  2. Parse the corresponding markdown file.
  3. Upsert the document row (keyed on external_id).
  4. Replace its chunks: delete existing rows, chunk + embed the body text,
     insert fresh rows.

One document failing never stops the run -- each is wrapped in its own
try/except and reported individually, with a summary at the end.

Usage:
    python3 ingest.py                              # ingest the whole corpus
    python3 ingest.py --only refunds_DE_enterprise_v2   # ingest a single doc
"""
import argparse
import json
import sys
from pathlib import Path

from supabase import create_client

from chunking import chunk_document
from config import ConfigError, get_settings
from parsing import parse_markdown_file
from providers.gemini_embedding import GeminiEmbeddingProvider

CORPUS_DIR = Path(__file__).parent / "corpus"
MANIFEST_PATH = CORPUS_DIR / "manifest.json"

REQUIRED_MANIFEST_FIELDS = ["id", "area", "jurisdiction", "status", "effective_from", "department"]
VALID_STATUSES = {"current", "superseded"}


class RejectedEntry(Exception):
    """Raised for a manifest entry that fails validation -- never reaches Supabase/Gemini."""


def validate_manifest_entry(entry):
    """Raise RejectedEntry with a human-readable reason if the entry is unusable."""
    for field in REQUIRED_MANIFEST_FIELDS:
        if not str(entry.get(field, "")).strip():
            raise RejectedEntry(f"missing required field '{field}'")

    if entry["status"] not in VALID_STATUSES:
        raise RejectedEntry(f"invalid status '{entry['status']}' (must be one of {sorted(VALID_STATUSES)})")

    if "filename" not in entry or not str(entry["filename"]).strip():
        raise RejectedEntry("missing required field 'filename'")


def _blank_to_none(value):
    """Manifest.json represents optional fields as "" instead of null."""
    if value is None:
        return None
    value = str(value).strip()
    return value or None


def build_document_row(entry, title, raw_text):
    return {
        "external_id": entry["id"],
        "title": title,
        "area": entry["area"],
        "jurisdiction": entry["jurisdiction"],
        "segment": _blank_to_none(entry.get("segment")),
        "status": entry["status"],
        "effective_from": entry["effective_from"],
        "effective_to": _blank_to_none(entry.get("effective_to")),
        "supersedes_external_id": _blank_to_none(entry.get("supersedes")),
        "department": entry["department"],
        "confidentiality": entry.get("confidentiality") or "internal",
        "raw_text": raw_text,
    }


def upsert_document(client, document_row):
    """Upsert by external_id and return the row's Supabase `id` (uuid)."""
    resp = client.table("documents").upsert(document_row, on_conflict="external_id").execute()
    if resp.data:
        return resp.data[0]["id"]

    # Some PostgREST configs don't return the row on upsert -- fall back to a lookup.
    sel = (
        client.table("documents")
        .select("id")
        .eq("external_id", document_row["external_id"])
        .single()
        .execute()
    )
    return sel.data["id"]


def replace_chunks(client, embedding_provider, document_id, title, body_text, max_words, overlap_words):
    """Delete existing chunks for this document, then chunk + embed + insert fresh ones."""
    client.table("chunks").delete().eq("document_id", document_id).execute()

    chunks = chunk_document(body_text, title, max_words, overlap_words)
    if not chunks:
        return 0

    embeddings = embedding_provider.embed_texts([c["chunk_text"] for c in chunks])

    rows = [
        {
            "document_id": document_id,
            "chunk_index": chunk["chunk_index"],
            "section_heading": chunk["section_heading"],
            "chunk_text": chunk["chunk_text"],
            "embedding": embedding,
        }
        for chunk, embedding in zip(chunks, embeddings)
    ]
    client.table("chunks").insert(rows).execute()
    return len(rows)


def process_entry(client, embedding_provider, entry, max_words, overlap_words):
    """Process one manifest entry end to end. Returns the number of chunks written."""
    md_path = CORPUS_DIR / entry["filename"]
    if not md_path.exists():
        raise FileNotFoundError(f"{md_path} does not exist")

    _metadata, title, body_text = parse_markdown_file(md_path)

    document_row = build_document_row(entry, title, body_text)
    document_id = upsert_document(client, document_row)

    return replace_chunks(client, embedding_provider, document_id, title, body_text, max_words, overlap_words)


def main():
    parser = argparse.ArgumentParser(description="Ingest the PolicyLens corpus into Supabase.")
    parser.add_argument("--only", help="Ingest a single document by its external_id, for testing.")
    args = parser.parse_args()

    try:
        settings = get_settings()
    except ConfigError as e:
        print(f"Configuration error: {e}")
        sys.exit(1)

    client = create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_KEY)
    embedding_provider = GeminiEmbeddingProvider(settings.GEMINI_API_KEY, settings.EMBEDDING_MODEL)

    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    if args.only:
        manifest = [e for e in manifest if e.get("id") == args.only]
        if not manifest:
            print(f"No manifest entry with id '{args.only}'")
            sys.exit(1)

    succeeded = failed = rejected = 0
    total_chunks = 0

    for entry in manifest:
        doc_id = entry.get("id", "<unknown>")
        try:
            validate_manifest_entry(entry)
        except RejectedEntry as e:
            print(f"REJECTED  {doc_id}: {e}")
            rejected += 1
            continue

        try:
            chunk_count = process_entry(client, embedding_provider, entry, settings.CHUNK_MAX_TOKENS, settings.CHUNK_OVERLAP_TOKENS)
            print(f"OK        {doc_id}: {chunk_count} chunks")
            succeeded += 1
            total_chunks += chunk_count
        except Exception as e:
            print(f"FAILED    {doc_id}: {e}")
            failed += 1

    print()
    print("=== Summary ===")
    print(f"Succeeded: {succeeded}")
    print(f"Failed:    {failed}")
    print(f"Rejected:  {rejected}")
    print(f"Total chunks written: {total_chunks}")

    if failed or rejected:
        sys.exit(1)


if __name__ == "__main__":
    main()
