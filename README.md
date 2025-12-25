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

4. Provide Supabase credentials to Streamlit (see `.streamlit/secrets.toml.example`).

5. Run locally:

```bash
streamlit run app.py
```

## 🏗️ Database Workflow (2025 Standard)

### 1. Apply Schema Changes
To push the optimized tables, indexes, and RLS policies defined in `supabase/migrations/` to the live database:

```bash
npx supabase db push

2. Seed Development Data
To purge existing test data and insert fresh records from supabase/seed.sql:
bash

cat supabase/seed.sql | npx supabase db query

Verwende Code mit Vorsicht.

    Note: You will be prompted for your Database Password.

3. Making Future Changes
Do not use the Supabase web UI to create tables or columns. To maintain version control:

    Generate a migration file:
    bash

    npx supabase migration new add_description_here

    Verwende Code mit Vorsicht.

Edit the file: Open the new .sql file in supabase/migrations/ and add your SQL commands.
Deploy: Run npx supabase db push.

📂 Project Structure

    supabase/migrations/ — Version-controlled database schema scripts.
    supabase/seed.sql — Script to populate the database with test data for development.
    .streamlit/secrets.toml — Local API credentials and connection strings

.
streamlit_app.py — The main Streamlit application entry point.

🆘 Troubleshooting



Development helpers
-------------------

You can purge and seed the development Supabase database using the included script `dev_db.py`.

Examples:

```bash
# To wipe and seed a user
python dev_db.py --purge --seed --yes --users user1@example.com

# To seed two users
python dev_db.py --seed --users user1@example.com user2@example.com
```

Deployment: push this repo to GitHub and deploy on Streamlit Cloud; set `SUPABASE_URL` and `SUPABASE_KEY` in the app secrets.
