-- PolicyLens -- migration 002: attach query_logs rows to a Supabase Auth user.
-- Run this in the Supabase SQL Editor (SQL Editor -> New query -> paste -> Run).
--
-- auth.users is created automatically by Supabase once Auth is enabled -- it is
-- NOT created here, only referenced.

alter table query_logs add column if not exists user_id uuid references auth.users(id);
create index if not exists idx_query_logs_user_id on query_logs (user_id);

-- Sanity check
select column_name, data_type
from information_schema.columns
where table_schema = 'public' and table_name = 'query_logs' and column_name = 'user_id';
