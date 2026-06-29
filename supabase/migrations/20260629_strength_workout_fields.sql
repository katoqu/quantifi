-- Add strength-workout fields for structured workout entries.
-- Existing simple metrics continue using the `value` column unchanged.

alter table if exists public.entries
  add column if not exists load_kg numeric;

alter table if exists public.entries
  add column if not exists sets jsonb default '[]'::jsonb;

comment on column public.entries.load_kg is 'Optional summary load for strength-style workout entries.';
comment on column public.entries.sets is 'Optional set-by-set workout structure for strength-style entries.';
