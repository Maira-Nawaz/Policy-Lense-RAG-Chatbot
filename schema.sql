-- PolicyLens \u2014 initial schema migration
-- Run this in Supabase SQL Editor (SQL Editor \u2192 New query \u2192 paste \u2192 Run)
-- Matches Architecture Design Document, Section 5.

-- 1. Enable pgvector (safe to re-run; no-op if already enabled)
create extension if not exists vector;

-- 2. documents
create table if not exists documents (
    id uuid primary key default gen_random_uuid(),
    external_id text unique not null,        -- matches corpus/manifest.json "id", e.g. "refunds_DE_enterprise_v2"
    title text not null,
    area text not null,
    jurisdiction text not null,
    segment text,                              -- nullable: enterprise / smb / full_time / contractor / null
    status text not null check (status in ('current', 'superseded')),
    effective_from date not null,
    effective_to date,                          -- null = currently open-ended
    supersedes_external_id text,                -- FK-by-value to another document's external_id
    department text not null,
    confidentiality text not null default 'internal',
    raw_text text not null,
    created_at timestamptz not null default now()
);

create index if not exists idx_documents_area_juris on documents (area, jurisdiction);
create index if not exists idx_documents_status on documents (status);

-- 3. chunks
-- Note: vector dimension (1536 below) must match your chosen embedding model's output size.
-- Common sizes: OpenAI text-embedding-3-small = 1536, Gemini text-embedding-004 = 768.
-- Adjust the dimension before running if you already know your embedding model.
create table if not exists chunks (
    id uuid primary key default gen_random_uuid(),
    document_id uuid not null references documents(id) on delete cascade,
    chunk_index int not null,
    section_heading text,
    chunk_text text not null,
    embedding vector(1536),
    created_at timestamptz not null default now()
);

create index if not exists idx_chunks_document_id on chunks (document_id);
-- Vector similarity index (created after you have data; ivfflat needs rows to build well).
-- Run this AFTER initial ingestion, not before:
-- create index idx_chunks_embedding on chunks using ivfflat (embedding vector_cosine_ops) with (lists = 50);

-- 4. query_logs
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
    provider text,                 -- which LLM provider/model served this request
    error_message text,            -- populated on system-level failure (distinct from a correct refusal)
    user_feedback text,            -- 'thumbs_up' / 'thumbs_down' / free text, nullable
    created_at timestamptz not null default now()
);

create index if not exists idx_query_logs_timestamp on query_logs ("timestamp");

-- 5. eval_runs
create table if not exists eval_runs (
    id uuid primary key default gen_random_uuid(),
    run_timestamp timestamptz not null default now(),
    config_snapshot jsonb,          -- embedding model, LLM provider, chunk size, thresholds, etc. used for this run
    retrieval_precision float8,
    retrieval_recall float8,
    groundedness_rate float8,
    refusal_correctness float8,
    p50_latency_ms int,
    p95_latency_ms int,
    total_cost_usd float8,
    notes text
);

-- 6. eval_results (one row per gold question per eval run)
create table if not exists eval_results (
    id uuid primary key default gen_random_uuid(),
    eval_run_id uuid not null references eval_runs(id) on delete cascade,
    eval_item_id text not null,          -- matches eval_set.json "id", e.g. "q001"
    expected_behavior text not null,
    actual_behavior text not null,
    retrieval_correct boolean,
    groundedness_score float8,
    behavior_correct boolean,
    query_log_id uuid references query_logs(id),
    created_at timestamptz not null default now()
);

create index if not exists idx_eval_results_run on eval_results (eval_run_id);

-- Sanity check: list all tables just created
select table_name
from information_schema.tables
where table_schema = 'public'
  and table_name in ('documents','chunks','query_logs','eval_runs','eval_results')
order by table_name;
