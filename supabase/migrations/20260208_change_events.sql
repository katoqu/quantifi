-- Add lifestyle change events (annotations) tied to existing categories

create table if not exists change_events (
  id uuid primary key default gen_random_uuid(),
  title text not null,
  notes text,
  recorded_at timestamp not null default now(),
  category_id uuid references categories(id) on delete set null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

create index if not exists change_events_user_id_idx on change_events (user_id);
create index if not exists change_events_recorded_at_idx on change_events (recorded_at);
create index if not exists change_events_category_id_idx on change_events (category_id);

alter table change_events enable row level security;

create policy "Users can manage their own change events" on change_events
  for all to authenticated using (auth.uid() = user_id);

