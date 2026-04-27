-- Add end-date lifecycle support for lifestyle change events.
alter table if exists change_events
  add column if not exists end_at timestamp;

alter table if exists change_events
  add column if not exists is_archived boolean not null default false;

create index if not exists change_events_is_archived_idx on change_events (is_archived);

-- Ensure change_events always has explicit RLS + owner-only policy.
alter table if exists public.change_events enable row level security;

drop policy if exists "Users can manage their own change events" on public.change_events;

create policy "Users can manage their own change events"
on public.change_events
for all
to authenticated
using (auth.uid() = user_id)
with check (auth.uid() = user_id);
