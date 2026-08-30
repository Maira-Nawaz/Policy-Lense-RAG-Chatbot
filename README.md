# PolicyLens

**An internal RAG (Retrieval-Augmented Generation) assistant that answers company policy questions — grounded in real documents, version-aware, jurisdiction-aware, and honest about what it doesn't know.**

https://github.com/Maira-Nawaz/Policy-Lense-RAG-Chatbot/blob/main/assets/home-page.png

---

## Table of Contents

1. [Problem & Motivation](#problem--motivation)
2. [What PolicyLens Does](#what-policylens-does)
3. [Architecture Overview](#architecture-overview)
4. [Tech Stack](#tech-stack)
5. [Data & Corpus Layer](#1-data--corpus-layer)
6. [Ingestion Pipeline](#2-ingestion-pipeline)
7. [Database Schema & SQL](#database-schema--sql)
8. [RAG Query Pipeline](#3-rag-query-pipeline)
9. [Evaluation Harness](#4-evaluation-harness)
10. [Backend API (FastAPI)](#5-backend-api-fastapi)
11. [Authentication](#6-authentication)
12. [Frontend (Next.js)](#7-frontend-nextjs)
13. [Cost Tracking](#8-cost-tracking)
14. [Setup & Local Development](#setup--local-development)
15. [Deployment](#deployment)
16. [Known Limitations & Future Work](#known-limitations--future-work)

---

## Problem & Motivation

Companies accumulate hundreds of internal policy documents — refund policies, data retention rules, PTO entitlements, expense reimbursement rules, data privacy procedures. These documents:

- **Change over time.** An old policy gets superseded by a new one, but the old version often stays accessible.
- **Differ by jurisdiction.** The same question ("what's our refund policy?") has a genuinely different correct answer in Germany, the US, and the UK.
- **Sometimes don't exist at all** for a specific combination of situation and jurisdiction.

A naive "chat with your documents" tool will confidently answer using whichever document is most *textually similar* to the question — even if it's outdated, or from the wrong country. That's a real operational and compliance risk, not just an inconvenience.

**PolicyLens is built specifically to handle this class of problem well:** it prefers the current version of a policy over a superseded one, it respects jurisdiction and customer-segment boundaries, and — critically — it **refuses to answer** rather than guess when no correct document exists for what's being asked.

> 📸 **Screenshot needed:** An example of the system correctly refusing (a "gap" question with no matching policy)

---

## What PolicyLens Does

A user asks a natural-language question like:

> "What is our refund policy for enterprise customers in Germany?"

PolicyLens:
1. Detects if the question is ambiguous (e.g. no jurisdiction given, but the answer depends on jurisdiction) and asks for clarification if so
2. Retrieves the most relevant policy document chunks using vector similarity search, filtered by jurisdiction/segment/validity date
3. Reranks the candidates against the specific question using a cross-encoder model
4. Generates an answer strictly grounded in the retrieved text, with a citation
5. **Forces a refusal** if the generated answer doesn't actually cite any retrieved document (a safeguard against silent hallucination)
6. Logs everything — the question, the answer, which documents were used, cost, latency — for every single query

> 📸 **Screenshot needed:** A version-conflict example (question answered using the *current* policy, not an outdated one)

---

## Architecture Overview

```
                     ┌─────────────────────┐
                     │   Next.js Frontend   │
                     │   (Vercel)           │
                     └──────────┬───────────┘
                                │ HTTPS
                     ┌──────────▼───────────┐
                     │   FastAPI Backend     │
                     │   (Render / Railway)  │
                     └──────────┬───────────┘
                                │
              ┌─────────────────┼─────────────────┐
              │                 │                 │
   ┌──────────▼─────────┐  ┌────▼─────┐   ┌───────▼────────┐
   │  Supabase           │  │  Gemini   │   │  Cross-encoder │
   │  (Postgres +        │  │  (embed + │   │  reranker      │
   │   pgvector + Auth)  │  │  generate │   │  (local, CPU)  │
   └──────────────────────┘  │  + judge) │   └────────────────┘
                              └───────────┘
```

**Design principle:** every model call (embedding, generation, judging) goes through a provider-agnostic interface, so swapping Gemini for a different provider later is a configuration change, not a rewrite.

> 📸 **Screenshot needed:** (optional) a cleaner version of this diagram, e.g. drawn in Excalidraw or similar

---

## Tech Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Next.js (App Router), TypeScript, Tailwind CSS | Modern React framework, strong AI-product ecosystem fit |
| Backend | FastAPI (Python) | Async-friendly, standard for serving LLM/RAG applications |
| Database + Vector Store | Supabase (Postgres + pgvector) | Metadata filtering and vector similarity in one SQL query; free tier |
| Authentication | Supabase Auth | Built-in, no separate auth service needed |
| Embeddings | Gemini `gemini-embedding-001` (768-dim) | Free tier, strong semantic quality |
| Generation & Judging | Gemini (model configurable via env) | Free tier; provider-agnostic interface allows swapping |
| Reranking | `cross-encoder/ms-marco-MiniLM-L-6-v2` (sentence-transformers) | Runs locally, no API cost, improves retrieval precision |
| Frontend Hosting | Vercel | Standard for Next.js, zero-config deploys |
| Backend Hosting | Render / Railway | Free tier suitable for a always-on Python service |

---

## 1. Data & Corpus Layer

Built before any AI/retrieval code — because every later tuning decision (chunking, thresholds, prompts) gets measured against this.

- **23 synthetic policy documents** (`corpus/*.md`), each with YAML front-matter metadata: `area`, `jurisdiction`, `segment`, `status`, `effective_from`/`effective_to`, `supersedes`, `department`, `confidentiality`.
- **5 policy areas × 3 jurisdictions** (Germany, US, UK), with segment splits where realistic (Enterprise vs. SMB refunds; full-time vs. contractor PTO).
- **5 deliberate version-conflict pairs** — a superseded document and its replacement with a *genuinely different rule*, not just a cosmetic date change. Example: Germany's enterprise refund window changed from 30 days to 14 days when the policy was rewritten to reflect that B2B contracts aren't covered by the statutory consumer withdrawal right.
- **3 deliberate gaps** (`corpus/known_gaps.json`) — jurisdiction/area/segment combinations with **no document at all**, specifically to test refusal behavior instead of the system fabricating an answer by analogy to a similar document.
- **`manifest.json` / `manifest.csv`** — structured index of every document; this seeds the Supabase `documents` table.
- **`eval/eval_set.json`** — 35 hand-authored gold question/answer pairs, each tagged with:
  - `expected_behavior`: `answer` / `clarify` / `refuse`
  - `expected_doc_ids`: the correct source document(s), where applicable
  - `category`: `straightforward_answerable`, `version_conflict`, `gap_refusal`, `ambiguous_no_jurisdiction`, `adversarial_distractor`, etc.

> 📸 **Screenshot needed:** A sample policy document with its YAML front-matter visible in the editor

---

## 2. Ingestion Pipeline

Turns the raw corpus into searchable vectors in Supabase.

- **`parsing.py`** — reads each markdown file's YAML front-matter and body text into a structured document object.
- **`chunking.py`** — splits each document into retrieval-sized chunks, respecting paragraph boundaries (never splitting a policy rule mid-sentence), with a sentence-level fallback for any paragraph that exceeds the chunk size on its own.
- **`providers/gemini_embedding.py`** — calls Gemini's `gemini-embedding-001` model (`output_dimensionality=768`) to embed each chunk. Retries on failure with exponential backoff; verifies the returned vector's dimension before accepting it.
- **`ingest.py`** — orchestrates the full flow: parse → validate metadata → chunk → embed → upsert into Supabase's `documents` table → delete-and-reinsert that document's `chunks` (so re-running ingestion never leaves stale chunks behind).
- **`config.py`** — central settings (model names, embedding dimension, chunking parameters), loaded from environment variables.

Run it with:
```bash
python ingest.py
python ingest.py --only <document_id>   # ingest a single document, for testing
```

> 📸 **Screenshot needed:** Terminal output of a successful `ingest.py` run showing all 23 documents processed

---

## Database Schema & SQL

All tables live in a single Supabase (Postgres) project, with the `pgvector` extension enabled for similarity search.

### Core schema

```sql
-- Enable pgvector
create extension if not exists vector;

-- Documents table
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    external_id text unique not null,
    title text not null,
    area text not null,
    jurisdiction text not null,
    segment text,
    status text not null check (status in ('current', 'superseded')),
    effective_from date not null,
    effective_to date,
    supersedes_external_id text,
    department text not null,
    confidentiality text not null default 'internal',
    raw_text text not null,
    created_at timestamptz not null default now()
);

-- Chunks table (768-dim vectors, matching Gemini's embedding model)
create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    section_heading text,
    chunk_text text not null,
    embedding vector(768),
    created_at timestamptz not null default now()
);

-- Query logs (every question asked, its answer, and full observability data)
create table if not exists query_logs (
    id uuid primary key default gen_random_uuid(),
    "timestamp" timestamptz not null default now(),
    query_text text not null,
    jurisdiction_given text,
    segment_given text,
    resolved_jurisdiction text,
    retrieved_chunk_ids uuid[] default '{}',
    answer_text text,
    is_refusal boolean not null default false,
    is_clarification boolean not null default false,
    groundedness_score float8,
    latency_ms int,
    prompt_tokens int,
    completion_tokens int,
    estimated_cost_usd float8,
    provider text,
    error_message text,
    user_feedback text,
    user_id uuid references auth.users(id),
    conversation_id uuid,
    archived boolean default false,
    reported boolean default false,
    report_reason text,
    created_at timestamptz not null default now()
);

-- Evaluation run summaries
create table if not exists eval_runs (
    id uuid primary key default gen_random_uuid(),
    run_timestamp timestamptz not null default now(),
    config_snapshot jsonb,
    retrieval_precision float8,
    retrieval_recall float8,
    groundedness_rate float8,
    refusal_correctness float8,
    p50_latency_ms int,
    p95_latency_ms int,
    total_cost_usd float8,
    notes text
);

-- Per-question evaluation results
create table if not exists eval_results (
    id uuid primary key default gen_random_uuid(),
    eval_run_id uuid not null references eval_runs(id) on delete cascade,
    eval_item_id text not null,
    expected_behavior text not null,
    actual_behavior text not null,
    retrieval_correct boolean,
    groundedness_score float8,
    behavior_correct boolean,
    query_log_id uuid references query_logs(id),
    created_at timestamptz not null default now()
);
```

### Vector similarity search function

Supabase can't perform metadata-filtered vector search through its standard table API — this Postgres function does both filtering and similarity ranking in a single database call:

```sql
create or replace function match_chunks(
    query_embedding vector(768),
    match_count int default 10,
    filter_jurisdiction text default null,
    filter_segment text default null,
    filter_department text default null,
    as_of_date date default current_date
)
returns table (
    chunk_id uuid,
    document_id uuid,
    chunk_text text,
    section_heading text,
    similarity float8,
    external_id text,
    title text,
    area text,
    jurisdiction text,
    segment text,
    status text,
    effective_from date,
    effective_to date,
    supersedes_external_id text,
    department text,
    confidentiality text
)
language sql stable
as $$
  select
    c.id as chunk_id,
    c.document_id,
    c.chunk_text,
    c.section_heading,
    1 - (c.embedding <=> query_embedding) as similarity,
    d.external_id, d.title, d.area, d.jurisdiction, d.segment, d.status,
    d.effective_from, d.effective_to, d.supersedes_external_id,
    d.department, d.confidentiality
  from chunks c
  join documents d on d.id = c.document_id
  where d.effective_from <= as_of_date
    and (d.effective_to is null or d.effective_to >= as_of_date)
    and (filter_jurisdiction is null or d.jurisdiction = filter_jurisdiction)
    and (filter_segment is null or d.segment = filter_segment or d.segment is null)
    and (filter_department is null or d.department = filter_department)
  order by c.embedding <=> query_embedding
  limit match_count;
$$;
```

### Migrations applied over the project's lifetime

| Migration | Purpose |
|---|---|
| `migration_001_fix_vector_dim.sql` | Corrected the `chunks.embedding` column from 1536 to 768 dimensions after switching embedding models |
| `migration_002_add_user_id.sql` | Added `user_id` to `query_logs` for per-user authentication and history |
| `migration_003_add_conversation_id.sql` | Added `conversation_id` to group individual queries into threaded conversations |
| `migration_004_*.sql` | Added `archived`, `reported`, `report_reason` columns for conversation management features |

> 📸 **Screenshot needed:** Supabase Table Editor showing the `documents` and `chunks` tables populated

---

## 3. RAG Query Pipeline

The core "ask a question, get a grounded answer" logic, in `rag_pipeline.py`.

**Flow, step by step:**

1. **Ambiguity detection** (`ambiguity.py`) — a cheap, deterministic, non-LLM rule check. If the question touches a policy area known to vary by jurisdiction and no jurisdiction was given, the system asks a clarifying question immediately (near-zero latency, no API cost) rather than guessing.
2. **Retrieval** — the question is embedded (using Gemini's query-optimized embedding mode) and passed to Supabase's `match_chunks` RPC, which performs metadata-filtered vector similarity search in one SQL call.
3. **Reranking** (`reranker.py`) — a local cross-encoder model re-scores the retrieved candidates against the exact question text, which is a stronger relevance signal than raw embedding similarity alone.
4. **Refusal check** — if zero candidates are returned, or the top reranked score falls below a threshold, the system refuses rather than forcing an answer from a weak match.
5. **Generation** (`providers/gemini_chat.py`) — Gemini generates an answer, instructed to cite only the retrieved documents and to say so explicitly if the context doesn't fully answer the question.
6. **Forced refusal on missing citation** — if the generated answer doesn't actually cite any of the retrieved documents (a sign the model may have blended in outside knowledge), the system overrides the result to a refusal rather than let an ungrounded answer through. This was added after evaluation testing surfaced exactly this failure mode (see [Evaluation Harness](#4-evaluation-harness)).
7. **Cost tracking** — token counts from the generation call are priced against `pricing.py`'s per-model rate table.
8. **Logging** — every query (question, retrieved chunks, answer, behavior, cost, latency, conversation ID) is written to `query_logs`, regardless of outcome.

A manual CLI test harness (`test_query.py`) exists for exercising this pipeline directly:
```bash
python test_query.py "What is our refund policy for enterprise customers in Germany?" --jurisdiction DE --segment enterprise --debug
```

> 📸 **Screenshot needed:** `test_query.py --debug` output showing reranked candidate scores

---

## 4. Evaluation Harness

Automated, repeatable scoring against the 35-item gold set — this is what turns "we built a RAG system" into "we measured it and can prove how well it works."

- **`judge.py`** — an LLM-as-judge that scores **groundedness** (is the generated answer actually supported by the retrieved text) using a separate model call, with a strict JSON-only response format and a retry-then-fallback path if parsing fails.
- **`run_eval.py`** — runs the full 35-question gold set through the actual production pipeline (no shortcuts), scoring:
  - **Retrieval precision/recall** — did the correct document get retrieved
  - **Groundedness rate** — is the answer supported by what was retrieved
  - **Refusal correctness** — did the system correctly refuse/clarify when it should have
  - Aggregates results into an `eval_runs` row (with a full config snapshot) and per-question detail into `eval_results`, enabling before/after comparison across iterations.
  - Handles Gemini's free-tier rate limits gracefully (parses `retryDelay` from 429 errors, `--delay` flag between items).

**Real before/after result from this project:**

| | Before fix | After fix |
|---|---|---|
| Behavior correct | 33/35 | **35/35** |
| Refusal correctness | 75% | **100%** |

The fix: adding the forced-refusal-on-missing-citation safeguard (step 6 above) and expanding the ambiguity detector's keyword coverage — both found by running the evaluation harness, not by manual testing.

```bash
python run_eval.py                # full 35-item run
python run_eval.py --limit 5       # quick partial run for iteration
```

> 📸 **Screenshot needed:** Terminal output of a full `run_eval.py` run showing the category breakdown
> 📸 **Screenshot needed:** The Metrics dashboard page showing eval run history and trend deltas

---

## 5. Backend API (FastAPI)

All endpoints in `api/main.py`.

| Endpoint | Method | Purpose |
|---|---|---|
| `/query` | POST | Runs a question through the RAG pipeline; returns answer, citations, behavior, cost, latency |
| `/feedback` | POST | Thumbs up/down on a specific answer, with ownership verification |
| `/conversations` | GET | Lists the authenticated user's conversations, grouped from `query_logs` |
| `/conversations/{id}/messages` | GET | Full message history for one conversation |
| `/conversations/{id}` | DELETE | Deletes a conversation (scoped to the owning user) |
| `/conversations/{id}/archive` | POST | Archives a conversation |
| `/conversations/{id}/report` | POST | Flags a conversation with a reason |
| `/eval-runs` | GET | Evaluation run history, powers the Metrics dashboard |
| `/history` | GET | Legacy flat query history (kept for backward compatibility) |
| `/health` | GET | Liveness check for deployment platforms |

Every user-scoped endpoint requires a valid Supabase session token (`Authorization: Bearer <token>`) via a `get_current_user` dependency, and filters all data access by the authenticated `user_id`.

A global exception handler ensures unhandled server errors still return proper CORS headers — without this, the browser reports genuine server errors as opaque "CORS blocked" failures, which is misleading to debug.

Interactive API docs are auto-generated at `/docs` (Swagger UI) — useful for manually testing endpoints without a frontend.

> 📸 **Screenshot needed:** The `/docs` Swagger UI page
> 📸 **Screenshot needed:** A successful `/query` response in Swagger UI

---

## 6. Authentication

Uses **Supabase Auth** end-to-end — no separate auth service or hand-rolled JWT verification.

- `get_current_user` (FastAPI dependency) verifies the incoming bearer token via `client.auth.get_user(token)` — token verification is delegated entirely to Supabase's SDK.
- Every data-access endpoint scopes its queries by the authenticated user's ID, so one user never sees another's conversations or feedback.
- Frontend: `/login` and `/signup` pages, an `AuthContext` holding the current session, and a `RequireAuth` wrapper that redirects unauthenticated visitors before any protected content renders.

> 📸 **Screenshot needed:** The login page
> 📸 **Screenshot needed:** The signup page

---

## 7. Frontend (Next.js)

Built with the App Router, TypeScript, and Tailwind CSS.

**Structure:**
- A shared layout (sidebar + auth guard) wraps both the Chat page and the Metrics dashboard, so the two share a consistent shell.
- State management via React Context: conversation reset/active-ID state, history selection (loading a past conversation into view), and the auth session.

**Chat page:**
- Question input with collapsible Jurisdiction/Segment options
- Markdown-rendered answers (proper bold/lists, not raw asterisks)
- Status pill per response: Answered / Needs clarification / Refused / Error
- Citations shown as a quiet footer after the answer
- Thumbs up/down feedback
- Cost and latency shown per answer
- Example/hard-case question chips on the empty state (straightforward, ambiguous, gap-in-corpus, version-conflict — each a real scenario the system is designed to handle correctly)

**History sidebar:**
- Search/filter, a Pinned section (client-side, localStorage), and the rest grouped by recency (Today / Yesterday / Previous 7 days / Older)
- Per-conversation menu: Share (an auth-gated deep link, not a public one, since a public link would bypass per-user access control), Archive, Report, Delete
- Collapsible/expandable, state persisted in `localStorage`

**Metrics page:**
- Stat cards for each evaluation metric with trend indicators vs. the previous run
- Full evaluation run history table
- Per-query cost/latency statistics

**Visual design:** went through several iterations (dark navy → light SaaS → a final light theme with an indigo accent, a light-neutral sidebar, and a compact two-line top bar) — all implemented via semantic Tailwind color tokens defined once and swapped centrally, rather than hardcoded colors scattered through components.

> 📸 **Screenshot needed:** Full chat interface with an example-question empty state
> 📸 **Screenshot needed:** A completed answer with citations, feedback buttons, and cost/latency shown
> 📸 **Screenshot needed:** The history sidebar with grouped/pinned conversations
> 📸 **Screenshot needed:** The Metrics dashboard

---

## 8. Cost Tracking

- **`pricing.py`** — a per-model $/million-token pricing table plus `estimate_cost_usd(model, prompt_tokens, completion_tokens)`.
- Threaded through the full chain: generation call → `rag_pipeline.py` → `query_logs.estimated_cost_usd` → API response → frontend display → `run_eval.py`'s `eval_runs.total_cost_usd`.
- **`backfill_costs.py`** — a one-time script that retroactively computed costs for queries and eval runs that were logged before cost tracking was fully wired up, so historical data isn't permanently blank.

> 📸 **Screenshot needed:** A chat response showing a real computed cost figure

---

## Setup & Local Development

### Prerequisites
- Python 3.11+
- Node.js 18+
- A free [Supabase](https://supabase.com) project
- A free [Google AI Studio](https://aistudio.google.com) API key (Gemini)

### 1. Clone and install backend dependencies
```bash
git clone <this-repo-url>
cd policylens
pip install -r requirements.txt
```

### 2. Set up Supabase
- Create a new Supabase project
- Enable the `pgvector` extension (Database → Extensions)
- Run the SQL in [Database Schema & SQL](#database-schema--sql) above, plus each migration file, in the SQL Editor
- Copy your project URL, anon key, and service role key from Project Settings → API

### 3. Configure environment variables
```bash
cp .env.example .env
```
Fill in `SUPABASE_URL`, `SUPABASE_SERVICE_KEY`, `GEMINI_API_KEY`, and the model settings.

### 4. Ingest the corpus
```bash
python ingest.py
```

### 5. Run the backend
```bash
python -m uvicorn api.main:app --reload --port 8000
```
Visit `http://localhost:8000/docs` to test endpoints directly.

### 6. Run the evaluation harness (optional, confirms everything works end-to-end)
```bash
python run_eval.py --limit 5
```

### 7. Set up and run the frontend
```bash
cd frontend
cp .env.local.example .env.local
# fill in NEXT_PUBLIC_SUPABASE_URL, NEXT_PUBLIC_SUPABASE_ANON_KEY, NEXT_PUBLIC_API_BASE_URL
npm install
npm run dev
```
Visit `http://localhost:3000`.

---

## Deployment

- **Backend**: deployed to [Render/Railway] — start command: `uvicorn api.main:app --host 0.0.0.0 --port $PORT`
- **Frontend**: deployed to Vercel, with `Root Directory` set to `frontend`
- **Auth**: Supabase's Redirect URLs configuration must include the deployed frontend's domain

Live demo: `[add deployed URL here]`

> 📸 **Screenshot needed:** The deployed app running at its live URL

---

## Known Limitations & Future Work

- **Retrieval precision** sits around 33% because the system retrieves the top 3 chunks per query even when usually only 1 is truly relevant — the reranker and generation prompt correctly filter this noise out, so it doesn't affect answer quality, but it's a known tuning target (reducing `TOP_K` or adjusting the reranker cutoff).
- **Free-tier hosting trade-offs**: the backend may spin down after inactivity (Render) or run on a time-limited trial credit (Railway), causing a slow first response after idle periods — a known, deliberate constraint given the project's zero-budget scope, not a bug.
- **Pricing figures** in `pricing.py` should be periodically re-verified against Gemini's current published pricing, since model pricing changes over time.
- **Hybrid search** (combining keyword search with vector similarity) is a reasonable future iteration for improving retrieval on queries with exact terminology matches.
- **Multi-tenant document management** (user-uploaded documents, real RBAC/access control) was deliberately scoped out — this project is intentionally narrow and deep on one hard retrieval problem rather than a general-purpose platform.


---


## Author

**Maira Nawaz** -- [GitHub](https://github.com/Maira-Nawaz) | [LinkedIn](https://www.linkedin.com/in/mairanawaz/)
