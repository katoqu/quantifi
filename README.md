# QuantifI (Simple Metric Tracker)

A minimal Streamlit app for manual metric tracking using Supabase (Postgres + Auth) as the backend.

**Docs**
- Testing: `docs/TESTING.md` (includes auto-generated test list)
- Documentation strategy: `docs/DOCUMENTATION.md`

## Features

- Supabase Auth sign-in + row-level security (RLS)
- Mobile-friendly tracker UI (overview / record / analytics / edit)
- Invite-only mode (optional) with in-app admin invites
- Import/export + basic DB admin tooling (`manage_db.py`)

## Quick start (local)

**Prereqs**
- Python 3.12 recommended
- A Supabase project (hosted or local)

1) Create and activate a virtual environment

```bash
python3 -m venv .venv
source .venv/bin/activate
```

2) Install dependencies

```bash
python3 -m pip install -r requirements.txt
```

3) Configure Streamlit secrets

Create `.streamlit/secrets.toml` (never commit real keys):

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-key>"
SUPABASE_SERVICE_ROLE_KEY = "<service-role-key>"  # needed for admin invites / manage_db
REDIRECT_URL = "http://localhost:8501"

# Optional (invite-only)
INVITE_ONLY = true
ADMIN_EMAILS = "you@example.com,other@example.com"

# Optional (manage_db DB connection)
DB_PASSWORD = "<db-password>"
```

4) Create database schema

This repo stores the schema as migrations under `supabase/migrations/`.

- Option A (recommended): Supabase CLI migrations

```bash
npx supabase db push
```

- Option B: SQL Editor
  - Copy/paste `supabase/migrations/schema.sql` into the Supabase SQL editor.

5) Run the app

```bash
streamlit run app.py
```

## Testing

```bash
python3 -m pytest
```

To keep `docs/TESTING.md` updated from test docstrings:

```bash
python3 scripts/update_test_docs.py
```

Optional auto-update on commit:

```bash
python3 -m pip install pre-commit
pre-commit install
```

## Database admin (`manage_db.py`)

The `manage_db.py` script is a development/admin helper (reads connection details from Streamlit secrets).

| Action | Command | Description |
| :--- | :--- | :--- |
| **Hard Reset** | `python3 manage_db.py --reset` | Wipes and seeds default development accounts via SQL. |
| **Purge User** | `python3 manage_db.py --purge --users email@example.com` | Deletes all data for specific users found via Supabase Auth. |
| **Seed User** | `python3 manage_db.py --seed --users email@example.com` | Seeds basic metrics + sample data for specific users. |

## Deployment (Streamlit Community Cloud)

If you want users to authenticate **only via Supabase**:

1) Set the Streamlit app visibility to **Public/Unlisted** (not Private), so users are not forced to log in to Streamlit.
2) Add the same secrets in the Streamlit Cloud “Secrets” UI.
3) In Supabase Auth, add your deployed app URL to allowed redirects (Auth → URL configuration).

## Inviting users (Streamlit vs Supabase)

There are **two different “invite” concepts** that can look similar:

- **Streamlit Community Cloud sharing invite** (viewer/collaborator for a *private* app)  
  This requires the user to **log in to Streamlit** before they can reach your app.
- **Supabase Auth invite** (creates an *app account* and emails an invite link)  
  This is what the app’s **Admin → Send Invite** uses.

### Invite-only access

For invite-only:

1) In Supabase Auth settings, disable self sign-ups.
2) Set `INVITE_ONLY = true` in Streamlit secrets (hides Sign Up UI + blocks sign-ups in code).
3) Set `ADMIN_EMAILS` in Streamlit secrets to enable the Admin page for those accounts.
4) Use **Admin → Send Invite** to email Supabase invite links.

The login screen shows a **Request access** button (mailto) when `INVITE_ONLY = true` and `ADMIN_EMAILS` is set.

## Security notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` secret. In Streamlit it stays server-side, but never print/log it.
- `.streamlit/` is ignored by git in this repo; rotate keys immediately if you ever commit them by accident.

## Inviting users (Streamlit vs Supabase)

There are **two different “invite” concepts** that can look similar:

- **Streamlit Community Cloud sharing invite** (adds someone as a viewer/collaborator for a *private* app)  
  This requires the user to **log in to Streamlit** before they can even reach your app.
- **Supabase Auth invite** (creates an *app account* in Supabase and emails the user an invite link)  
  This is what `auth.py` / `auth_engine.py` implement for in-app sign-in and user identity.

### Recommended setup (single login)

If you want users to only authenticate once (via Supabase):

1. Set the deployed Streamlit app visibility to **Public/Unlisted** (not Private).
2. Use Supabase Auth for sign-in/sign-up (the UI in this repo).

### Invite-only access (optional)

If you want invite-only:

- Set the Streamlit app visibility to **Public/Unlisted** (so users don’t need a Streamlit account).
- Disable self-signups in **Supabase Auth** settings (so only invited users can create accounts).
- Set `INVITE_ONLY = true` in Streamlit secrets (this hides the Sign Up UI and blocks sign-ups in code).
- Set `ADMIN_EMAILS` in Streamlit secrets (comma-separated) to enable the **Admin** page.
- Use the app’s **Admin → Send Invite** to send a Supabase Auth invite email.
- The login screen shows a **Request access** button (mailto) when `INVITE_ONLY = true` and `ADMIN_EMAILS` is set.

Secrets used:
- `REDIRECT_URL`: where Supabase will redirect after email links (password recovery / invite / verification).
- `ADMIN_EMAILS`: comma-separated list of admin emails (e.g. `"you@example.com,other@example.com"`).
- `INVITE_ONLY`: boolean (`true`/`false`) to disable self sign-ups in the app UI/logic.
