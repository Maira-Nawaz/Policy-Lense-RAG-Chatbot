-- PolicyLens -- migration 004: archive/report flags for conversation management
-- (Share and Pin do not need schema changes -- Share reuses existing per-user
-- scoping, Pin is stored client-side in localStorage.)
-- Run this in the Supabase SQL Editor (SQL Editor -> New query -> paste -> Run).
--
-- not null default false backfills every existing row automatically -- no
-- separate backfill script needed (unlike conversation_id, which was left
-- nullable on purpose).

alter table query_logs add column if not exists archived boolean not null default false;
alter table query_logs add column if not exists reported boolean not null default false;
alter table query_logs add column if not exists report_reason text;

-- Sanity check
select column_name, data_type, is_nullable, column_default
from information_schema.columns
where table_schema = 'public' and table_name = 'query_logs'
  and column_name in ('archived', 'reported', 'report_reason');
