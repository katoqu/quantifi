-- 1. EXTENSIONS
create extension if not exists "pgcrypto";

-- 2. TABLES 

-- Categories remain as they were
create table categories (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

-- Metrics table now includes unit and range metadata directly
-- It also includes the logic check for integer ranges.
create table metrics (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  unit_name text,
  unit_type text default 'float', -- Options: float, integer, integer_range
  range_start integer,
  range_end integer,
  category_id uuid references categories(id) on delete set null,
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now(),
  
  -- CONSTRAINT: Enforce valid range logic at the definition level
  CONSTRAINT check_range_logic CHECK (
    (unit_type = 'integer_range' AND range_end > range_start) OR 
    (unit_type != 'integer_range')
  )
);

create table entries (
  id uuid primary key default gen_random_uuid(),
  metric_id uuid references metrics(id) on delete cascade,
  value numeric,
  recorded_at timestamp not null, -- Support for specific times
  user_id uuid not null references auth.users default auth.uid(),
  created_at timestamptz default now()
);

-- 3. INDEXES
create unique index categories_name_user_idx on categories (lower(name), user_id);
create index entries_metric_id_idx on entries (metric_id);
create index entries_recorded_at_idx on entries (recorded_at);
create index metrics_category_id_idx on metrics (category_id);

-- 4. SECURITY (RLS)
alter table categories enable row level security;
alter table metrics enable row level security;
alter table entries enable row level security;

-- 5. POLICIES
create policy "Users can manage their own categories" on categories
  for all to authenticated using (auth.uid() = user_id);

create policy "Users can manage their own metrics" on metrics
  for all to authenticated using (auth.uid() = user_id);

create policy "Users can manage their own entries" on entries
  for all to authenticated using (auth.uid() = user_id);

-- 6. VALIDATION TRIGGER
-- Prevents entries from being saved if they violate a metric's integer_range bounds.

CREATE OR REPLACE FUNCTION validate_entry_range()
RETURNS TRIGGER AS $$
DECLARE
    m_type TEXT;
    m_start INT;
    m_end INT;
BEGIN
    -- Fetch metric metadata
    SELECT unit_type, range_start, range_end 
    INTO m_type, m_start, m_end
    FROM metrics 
    WHERE id = NEW.metric_id;

    -- Validate only if type is integer_range
    IF m_type = 'integer_range' THEN
        IF NEW.value < m_start OR NEW.value > m_end THEN
            RAISE EXCEPTION 'Value % is out of range (% to %)', NEW.value, m_start, m_end;
        END IF;
    END IF;

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_validate_entry_range
BEFORE INSERT OR UPDATE ON entries
FOR EACH ROW
EXECUTE FUNCTION validate_entry_range();