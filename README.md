# Simple Metric Tracker

Minimal Streamlit app for manual metric tracking using Supabase as the backend.

Docs:
- Testing: `docs/TESTING.md`
- Documentation strategy: `docs/DOCUMENTATION.md`

Quick start (local):

1. Create and activate a virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2. Install dependencies:

```bash
pip install -r requirements.txt
```

3. Create a Supabase project and run the SQL in `schema.sql` to create tables.

```bash
npx supabase db push
```


4. 🛠️ Database Management

The project uses Supabase (PostgreSQL) with a unified schema that handles metrics, categories, and data entries. Business logic for value ranges is enforced at both the UI level and the database level.
 
    1. Initial Setup

        To set up or completely reset the database structure, execute the contents of schema.sql in the Supabase SQL Editor. This script: 
        
        - Drops existing objects: Clears existing tables, triggers, and functions to ensure a clean state.

        - Creates unified tables: Sets up categories, metrics, and entries.

        - *Enforces range logic*: Adds a CHECK constraint to the metrics table to ensure range_end > range_start for integer ranges.

        Installs Validation Triggers: Prevents out-of-range data entry at the database level via the validate_entry_range function.

    2. **Administrative Tool(manage_db.py)**
    The manage_db.py script is a consolidated tool for development and administration. It replaces older legacy scripts (reseed.py, dev_db.py, seed.sql).

| Action | Command | Description |
| :--- | :--- | :--- |
| **Hard Reset** | `python manage_db.py --reset` | Wipes and seeds default development accounts via high-speed SQL. |
| **Purge User** | `python manage_db.py --purge --users email@example.com` | Deletes all data for a specific user found via Supabase Auth. |
| **Seed User** | `python manage_db.py --seed --users email@example.com` | Seeds basic metrics and sample data for a specific user. |


    4. **Reset & Seed (Development)**
    To purge existing test data and populate the database with fresh random records for development, use the included Python script. It automatically reads your connection details from Streamlit secrets.


5. Making Future Changes
To maintain version control, never create tables directly in the Supabase Web UI:

    1 Generate migration: npx supabase migration new add_description_here
    2. Edit: Open the new .sql file in supabase/migrations/ and add your SQL commands.
    3. Deploy: Run npx supabase db push.

6. Run locally:

```bash
streamlit run app.py
```

Testing:

```bash
python3 -m pytest
```

Specific regression tests:

```bash
python3 -m pytest tests/test_visualize_stats.py
```
