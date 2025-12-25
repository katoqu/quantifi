-- 1. EXTENSIONS
create extension if not exists "pgcrypto";

-- 2. TABLES 
-- Created with all columns, constraints, and defaults from the start

create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

create table units (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  unit_type text default 'float',
  range_start integer,
  range_end integer,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

create table metrics (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  category_id uuid references categories(id) on delete set null,
  unit_id uuid references units(id) on delete set null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

create table entries (
  id uuid primary key default gen_random_uuid(),
  metric_id uuid references metrics(id) on delete cascade,
  value numeric,
  recorded_at date not null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

-- 3. INDEXES
-- Enforce case-insensitive uniqueness per user
create unique index categories_name_user_idx on categories (lower(name), user_id);
create unique index units_name_user_idx on units (lower(name), user_id);

-- Performance indexes
create index entries_metric_id_idx on entries (metric_id);
create index entries_recorded_at_idx on entries (recorded_at);
create index metrics_category_id_idx on metrics (category_id);
create index metrics_unit_id_idx on metrics (unit_id);

-- 4. SECURITY (RLS)
alter table categories enable row level security;
alter table units enable row level security;
alter table metrics enable row level security;
alter table entries enable row level security;

-- 5. POLICIES
-- Create policies for all tables using a standardized naming convention
create policy "Users can manage their own categories" on categories
  for all to authenticated using (auth.uid() = user_id);

create policy "Users can manage their own units" on units
  for all to authenticated using (auth.uid() = user_id);

create policy "Users can manage their own metrics" on metrics
  for all to authenticated using (auth.uid() = user_id);

create policy "Users can manage their own entries" on entries
  for all to authenticated using (auth.uid() = user_id);
