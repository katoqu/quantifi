create extension if not exists "pgcrypto";

-- Lookup tables (LOV) for categories and units
create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);
create unique index on categories (name);

create table units (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);
create unique index on units (name);

-- Metrics reference category and unit by id (LOV)
create table metrics (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  category_id uuid references categories(id) on delete set null,
  unit_id uuid references units(id) on delete set null,
  created_at timestamptz default now()
);

create table entries (
  id uuid primary key default gen_random_uuid(),
  metric_id uuid references metrics(id) on delete cascade,
  value numeric,
  recorded_at date not null,
  created_at timestamptz default now()
);

create index on entries (metric_id);
create index on entries (recorded_at);

-- Helpful indexes for lookups
create index on metrics (category_id);
create index on metrics (unit_id);

-- Example seed values (optional):
-- insert into categories (name) values ('Body'), ('Performance'), ('Sleep');
-- insert into units (name) values ('kg'), ('lb'), ('reps'), ('minutes');