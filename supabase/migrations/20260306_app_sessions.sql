-- Server-side session persistence for Streamlit deployments
-- Stores encrypted Supabase tokens keyed by an opaque session id (SID).

create table if not exists public.app_sessions (
  id uuid primary key,
  user_id uuid not null references auth.users (id) on delete cascade,
  token_blob text not null,
  created_at bigint not null,
  last_seen_at bigint not null,
  revoked_at bigint,
  max_age_days int not null default 30
);

-- Lock this table down. The Streamlit app accesses it using the service role key.
alter table public.app_sessions enable row level security;

revoke all on table public.app_sessions from anon;
revoke all on table public.app_sessions from authenticated;

