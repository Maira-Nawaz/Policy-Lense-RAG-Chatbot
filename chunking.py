"""
Splits a document body into retrieval chunks.

Strategy: group whole paragraphs (blank-line separated) up to max_words per
chunk. A paragraph is never split mid-sentence -- if a single paragraph is
larger than max_words on its own, it falls back to sentence-level grouping,
and only if a single sentence is itself larger than max_words does it get a
hard word-level split (the one case where a sentence is split at all).

"Words" (whitespace-separated tokens) are used as a cheap stand-in for LLM
tokens -- good enough for chunk sizing without pulling in a tokenizer.
"""
import re

_PARAGRAPH_SPLIT_RE = re.compile(r"\n\s*\n")
_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?])\s+")


def _split_paragraphs(text):
    return [p.strip() for p in _PARAGRAPH_SPLIT_RE.split(text.strip()) if p.strip()]


def _split_sentences(text):
    return [s.strip() for s in _SENTENCE_SPLIT_RE.split(text.strip()) if s.strip()]


def _word_count(text):
    return len(text.split())


def _tail_words(text, n):
    """Last n whitespace-separated words of text, used to seed overlap."""
    if n <= 0:
        return ""
    words = text.split()
    return " ".join(words[-n:])


def _chunk_oversized_paragraph(paragraph, max_words, overlap_words):
    """Sentence-level fallback for a paragraph that alone exceeds max_words."""
    sentences = _split_sentences(paragraph)
    chunks = []
    current = []
    current_words = 0

    for sentence in sentences:
        sentence_words = _word_count(sentence)

        if sentence_words > max_words:
            # Single sentence is bigger than a whole chunk -- the only case
            # where we split inside a sentence, at the word level.
            if current:
                chunks.append(" ".join(current))
                current, current_words = [], 0
            words = sentence.split()
            for i in range(0, len(words), max_words):
                chunks.append(" ".join(words[i:i + max_words]))
            continue

        if current and current_words + sentence_words > max_words:
            chunks.append(" ".join(current))
            overlap_text = _tail_words(chunks[-1], overlap_words)
            current = [overlap_text] if overlap_text else []
            current_words = _word_count(overlap_text)

        current.append(sentence)
        current_words += sentence_words

    if current:
        chunks.append(" ".join(current))

    return chunks


def chunk_document(body_text, title, max_words, overlap_words):
    """Chunk a document body into a list of dicts ready for the `chunks` table.

    Returns:
        list of {"chunk_index": int, "section_heading": str, "chunk_text": str}
    """
    paragraphs = _split_paragraphs(body_text)

    chunk_texts = []
    current_paragraphs = []
    current_words = 0

    def flush():
        nonlocal current_paragraphs, current_words
        if current_paragraphs:
            chunk_texts.append("\n\n".join(current_paragraphs))
        current_paragraphs, current_words = [], 0

    for paragraph in paragraphs:
        paragraph_words = _word_count(paragraph)

        if paragraph_words > max_words:
            flush()
            chunk_texts.extend(_chunk_oversized_paragraph(paragraph, max_words, overlap_words))
            continue

        if current_paragraphs and current_words + paragraph_words > max_words:
            flush()
            overlap_text = _tail_words(chunk_texts[-1], overlap_words) if chunk_texts else ""
            if overlap_text:
                current_paragraphs = [overlap_text]
                current_words = _word_count(overlap_text)

        current_paragraphs.append(paragraph)
        current_words += paragraph_words

    flush()

    return [
        {"chunk_index": i, "section_heading": title, "chunk_text": text}
        for i, text in enumerate(chunk_texts)
    ]
