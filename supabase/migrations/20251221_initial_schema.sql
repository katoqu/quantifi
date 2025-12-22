-- Combined DB initialization for Quantifi
-- Merged from: 20251221 inital schema.sql and 20251222_add_unit_metadata.sql

-- Enable pgcrypto for gen_random_uuid()
create extension if not exists "pgcrypto";

-- Lookup tables (LOV) for categories and units
create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  created_at timestamptz default now()
);

-- Enforce case-insensitive uniqueness on category names
create unique index on categories (lower(name));

create table units (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  -- Metadata to support unit types and integer ranges
  unit_type text default 'float',
  range_start integer,
  range_end integer,
  created_at timestamptz default now()
);

-- Enforce case-insensitive uniqueness on unit names
create unique index on units (lower(name));

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

-- Helpful indexes for lookups and performance
create index on entries (metric_id);
create index on entries (recorded_at);
create index on metrics (category_id);
create index on metrics (unit_id);

-- Optional seed values (uncomment to insert):
-- insert into categories (name) values ('body'), ('performance'), ('sleep');
-- insert into units (name, unit_type) values ('kg', 'float'), ('lb', 'float'), ('reps', 'int'), ('minutes', 'int');

-- Notes:
-- * This file enforces case-insensitive uniqueness for `categories.name` and `units.name` by using
--   indexes on lower(name). If you prefer case-sensitive uniqueness, replace those indexes with
--   `CREATE UNIQUE INDEX ON <table> (name);` instead.
-- * The `unit_type` field defaults to 'float'. Use 'int' for integer-only units and set
--   `range_start`/`range_end` when applicable.
