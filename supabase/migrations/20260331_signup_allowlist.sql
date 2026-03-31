create table if not exists public.signup_allowlist (
  email text primary key,
  created_at timestamptz not null default now()
);

alter table public.signup_allowlist enable row level security;
