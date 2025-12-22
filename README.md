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

Development helpers
-------------------

You can purge and seed the development Supabase database using the included script `dev_db.py`.

Examples:

```bash
# Purge all data (interactive confirmation)
python dev_db.py --purge

# Purge without prompt and then seed sample data
python dev_db.py --both --yes

# Only seed sample data
python dev_db.py --seed
```

Deployment: push this repo to GitHub and deploy on Streamlit Cloud; set `SUPABASE_URL` and `SUPABASE_KEY` in the app secrets.
