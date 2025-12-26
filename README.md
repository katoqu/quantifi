# Simple Metric Tracker

Minimal Streamlit app for manual metric tracking using Supabase as the backend.

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


4. Reset & Seed (Development)
To purge existing test data and populate the database with fresh random records for development, use the included Python script. It automatically reads your connection details from Streamlit secrets.

```bash
# Purge and Reseed database for defined test users
python reseed.py
```bash
Note: This script deletes existing entries for the target UUIDs and generates new data for the last 7 days.

5. Making Future Changes
To maintain version control, never create tables directly in the Supabase Web UI:

    1 Generate migration: npx supabase migration new add_description_here
    2. Edit: Open the new .sql file in supabase/migrations/ and add your SQL commands.
    3. Deploy: Run npx supabase db push.

6. Run locally:

```bash
streamlit run app.py
```