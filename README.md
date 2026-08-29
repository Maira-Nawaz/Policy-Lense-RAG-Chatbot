# PolicyLens \u2014 Synthetic Corpus & Gold Evaluation Set

This is the data layer described in the PRD (Section 8) and Architecture Design Document
(Sections 5\u20137). It exists before any retrieval/generation code because the evaluation set is
what every later architecture decision (chunking strategy, embedding model, reranker threshold,
refusal logic) gets tuned against.

## Contents

```
policylens/
  generate_corpus.py       # generates the corpus from a hardcoded manifest \u2014 re-run any time you edit it
  corpus/
    *.md                   # 23 policy documents, each with YAML front-matter metadata
    manifest.json           # structured index of all documents (seeds the Supabase `documents` table)
    manifest.csv             # same, as CSV
    known_gaps.json          # explicit list of area/jurisdiction/segment combos with NO document (by design)
  eval/
    eval_set.json           # 35 gold question/answer pairs used by the evaluation harness
```

## Corpus design (scope note)

The corpus is **23 documents**, not a round 40/60. Every document exists to create a specific,
deliberate hard case rather than to pad a count:

- **5 policy areas**: refunds, data retention, PTO, expense reimbursement, data privacy (subject
  access requests)
- **3 jurisdictions**: Germany (DE), United States (US), United Kingdom (UK)
- **Segment splits** where realistic: refunds (Enterprise vs. SMB), PTO (full-time vs. contractor)
- **5 version-conflict pairs**: a superseded document plus the current document that replaced it,
  with a genuinely different rule (not just a cosmetic date change) \u2014 e.g. Germany's enterprise
  refund window went from 30 days to 14 days when the policy was rewritten to reflect that B2B
  contracts aren't covered by the statutory consumer withdrawal right.
- **3 deliberate gaps** (see `known_gaps.json`): area/jurisdiction/segment combinations where no
  document exists at all, specifically to test whether the system correctly refuses instead of
  fabricating an answer by analogy to a similar document.

Every document's legal/policy detail (statutory references, day counts, thresholds) was written
to be internally consistent and jurisdiction-plausible, so retrieval failures in testing reflect
real ambiguity in the text, not arbitrary randomness.

## Metadata schema (per document, in the YAML front-matter and manifest)

| Field | Meaning |
|---|---|
| `id` | Unique document id, matches filename |
| `area` | Policy area (refunds, data_retention, pto, expense_reimbursement, data_privacy) |
| `jurisdiction` | DE / US / UK |
| `segment` | enterprise / smb / full_time / contractor / null |
| `status` | current / superseded |
| `effective_from` / `effective_to` | Validity window; `effective_to: null` means currently open-ended |
| `supersedes` | id of the document this one replaces, if any |
| `department` | Owning internal department (Finance, HR, Legal) |
| `confidentiality` | Confidentiality level (all currently `internal`) |

This maps directly to the `documents` table schema in the Architecture Design Document, Section 5.1.

## Gold evaluation set (`eval/eval_set.json`)

35 hand-authored question/answer items. Each item specifies:

- `expected_behavior`: one of `answer`, `clarify`, `refuse`
- `expected_doc_ids`: the correct source document(s) for `answer` items (empty for `clarify`/`refuse`)
- `category`: what kind of hard case this tests

### Category breakdown

| Category | Count | Tests |
|---|---|---|
| straightforward_answerable | 18 | Basic retrieval correctness per document |
| version_conflict | 6 | System must prefer the *current* document, not a superseded one |
| version_conflict_explicit_historical | 1 | System must still surface superseded content when explicitly asked about history |
| gap_refusal | 3 | System must refuse when no document exists for the exact combination asked |
| gap_refusal_out_of_corpus_jurisdiction / area | 2 | System must refuse for jurisdictions/topics not in the corpus at all, not generalise from similar content |
| ambiguous_no_jurisdiction | 3 | System must ask for clarification (or explicitly summarise variants) rather than silently picking one jurisdiction |
| adversarial_distractor | 2 | System must not let a change to one document incorrectly bleed into its reasoning about a related-but-separate document |

### How this will be scored (per Architecture Design Document, Section 7)

- **Retrieval precision/recall**: did the retrieved chunks come from `expected_doc_ids`
- **Groundedness**: for `answer` items, is the generated answer actually supported by the
  retrieved text (LLM-as-judge + periodic human spot-check)
- **Refusal correctness**: for `clarify`/`refuse` items, did the system correctly decline to give
  a confident single-jurisdiction answer

## Regenerating the corpus

If you edit `generate_corpus.py` (e.g. to add more documents), just re-run:

```bash
python3 generate_corpus.py
```

This overwrites `corpus/*.md` and the manifest files. It does **not** touch `eval/eval_set.json`
\u2014 if you add/remove documents, check whether any eval items need updating (the validation
snippet below will catch broken references).

## Validating eval set integrity

Run this any time you change either the corpus or the eval set, to catch broken references before
they cause confusing evaluation-harness failures later:

```bash
python3 -c "
import json
manifest = json.load(open('corpus/manifest.json'))
valid_ids = {d['id'] for d in manifest}
eval_set = json.load(open('eval/eval_set.json'))
errors = []
for item in eval_set['items']:
    for doc_id in item['expected_doc_ids']:
        if doc_id not in valid_ids:
            errors.append(f\"{item['id']}: unknown doc_id {doc_id}\")
print('OK' if not errors else errors)
"
```

## Next step

With this in place, the next build phase (per the Architecture Design Document) is the
ingestion/indexing pipeline: parsing these markdown files, chunking them, embedding the chunks,
and writing them into Supabase/pgvector \u2014 followed by the query-time retrieval + generation
service, and finally the evaluation harness that runs `eval_set.json` end-to-end through that
pipeline.

## Running the API locally

`api/main.py` wraps `rag_pipeline.answer_query()` in a FastAPI app (`POST /query`, `POST
/feedback`, `GET /health`) so a frontend can call PolicyLens over HTTP. Run it from the project
root (so the top-level modules like `rag_pipeline` and `config` are importable):

```bash
uvicorn api.main:app --reload --port 8000
```

Then open http://localhost:8000/docs for an interactive Swagger UI \u2014 you can try both
`/query` and `/feedback` directly from the browser without needing curl or a frontend.
