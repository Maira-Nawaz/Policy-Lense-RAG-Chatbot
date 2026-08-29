-- PolicyLens -- migration 003: group query_logs rows into conversations.
-- Run this in the Supabase SQL Editor (SQL Editor -> New query -> paste -> Run).
--
-- Nullable and unbackfilled on purpose: existing rows get conversation_id = null.
-- The API treats each such legacy row as its own single-message conversation
-- (using the row's own id as the conversation_id for grouping) rather than
-- merging old questions together or hiding them -- see api/main.py's
-- /conversations and /conversations/{conversation_id}/messages.

alter table query_logs add column if not exists conversation_id uuid;
create index if not exists idx_query_logs_conversation_id on query_logs (conversation_id);

-- Sanity check
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'query_logs' and column_name = 'conversation_id';
