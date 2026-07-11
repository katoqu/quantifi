# QuantifI (Simple Metric Tracker)

A minimal Streamlit app for manual metric tracking using Supabase (Postgres + Auth) as the backend.

**Docs**
- Testing: `docs/TESTING.md` (includes auto-generated test list)
- Documentation strategy: `docs/DOCUMENTATION.md`

## Features

- Supabase Auth sign-in + row-level security (RLS)
- Mobile-friendly tracker UI (home / add / log / stats / edit)
- Allowlist-based signup approval (no email required)
- Import/export + basic DB admin tooling (`manage_db.py`)

## Quick start (local)

**Prereqs**
- Python 3.12 recommended
- A Supabase project (hosted or local)
- UV (recommended) or pip for dependency management

### Virtual Environment Setup

This project supports two virtual environments:
- `.venv/` (primary, recommended) - Uses Python 3.12.3
- `venv/` (backup) - Older environment for compatibility

**Recommended: Use `.venv/` with UV (fast and reproducible)**

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies using UV (recommended)
uv sync
```

**Alternative: Traditional pip approach**

```bash
# Create and activate virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies using pip
python3 -m pip install -r requirements.txt
```

If your IDE shows import resolution errors (e.g. `streamlit` / `pandas`), point it at `.venv/bin/python` (VS Code also picks this up from `.vscode/settings.json`).

3) Configure Streamlit secrets

Create `.streamlit/secrets.toml` (never commit real keys):

```toml
SUPABASE_URL = "https://<project-ref>.supabase.co"
SUPABASE_KEY = "<anon-key>"
SUPABASE_SERVICE_ROLE_KEY = "<service-role-key>"  # needed for admin allowlist / manage_db
REDIRECT_URL = "http://localhost:8501"

# Optional (allowlist signups without email)
SIGNUP_ALLOWLIST_ENABLED = true
SIGNUP_ALLOWLIST_TABLE = "signup_allowlist"

# Optional
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

## UV vs Traditional Virtual Environments

This project supports both modern UV and traditional pip workflows:

### UV (UltraViolet) - Recommended

**Features:**
- ✅ Very fast dependency resolution (Rust-based)
- ✅ Automatic lock file (`uv.lock`) for reproducibility
- ✅ Uses `pyproject.toml` as primary dependency source
- ✅ Excellent for production deployments

**Commands:**
```bash
# Install UV (if not already installed)
curl -LsSf https://astral.sh/uv/install.sh | sh

# Add a dependency
uv add package-name

# Update lock file
uv lock

# Sync dependencies (install from lock file)
uv sync

# Install globally (for production)
uv sync --system
```

### Traditional Pip Approach

**Features:**
- ✅ Familiar workflow for Python developers
- ✅ Uses `requirements.txt` as primary dependency source
- ✅ Works without additional tools
- ⚠️ Slower dependency resolution

**Commands:**
```bash
# Create virtual environment
python3 -m venv .venv

# Activate
source .venv/bin/activate

# Install dependencies
python3 -m pip install -r requirements.txt

# Freeze dependencies (manual lock)
pip freeze > requirements.txt
```

### Key Differences

| Aspect | UV Approach | Traditional Pip Approach |
|--------|-------------|--------------------------|
| **Dependency File** | `pyproject.toml` + `uv.lock` | `requirements.txt` |
| **Speed** | Very fast (Rust-based) | Slower (Python-based) |
| **Lock File** | Automatic (`uv.lock`) | Manual (`pip freeze`) |
| **Reproducibility** | Excellent | Good |
| **Ecosystem** | Modern (PEP 621) | Traditional |

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

### Production Deployment with UV (Recommended)

```bash
# Install dependencies globally using UV
uv sync --system

# OR install in a virtual environment
python3 -m venv .venv
source .venv/bin/activate
uv sync
```

### Traditional Pip Deployment

```bash
# Install dependencies using pip
python3 -m pip install -r requirements.txt
```

If you want users to authenticate **only via Supabase**:

1) Set the Streamlit app visibility to **Public/Unlisted** (not Private), so users are not forced to log in to Streamlit.
2) Add the same secrets in the Streamlit Cloud “Secrets” UI.
3) In Supabase Auth, add your deployed app URL to allowed redirects (Auth → URL configuration).

### Allowlist signup (no email)

If you want users to sign up **only after you approve them**, without sending any emails:

1) Create an allowlist table in Supabase (see SQL below).
2) Set `SIGNUP_ALLOWLIST_ENABLED = true` in Streamlit secrets.
3) Set `ADMIN_EMAILS` in Streamlit secrets to enable the Admin page.
4) Use **Admin → Approve Signup** to add emails to the allowlist.

Allowlist table SQL:

```sql
create table if not exists public.signup_allowlist (
  email text primary key,
  created_at timestamptz not null default now()
);
```

## Virtual Environment Troubleshooting

### Common Issues and Solutions

**Issue: "Module not found" after activation**
- Ensure you're using the correct Python interpreter: `.venv/bin/python`
- Check that dependencies are installed in the active environment
- Try reinstalling: `uv sync` or `pip install -r requirements.txt`

**Issue: UV commands not found**
- Install UV first: `curl -LsSf https://astral.sh/uv/install.sh | sh`
- Ensure `~/.local/bin` is in your PATH

**Issue: Dependency conflicts**
- Delete the lock file and regenerate: `rm uv.lock && uv lock`
- Or recreate virtual environment: `rm -rf .venv && python3 -m venv .venv`

**Issue: Slow dependency installation**
- Use UV instead of pip for faster resolution: `uv sync`
- UV is typically 10-100x faster than pip

**Issue: Production deployment failures**
- Ensure `uv.lock` is committed and up-to-date
- Use `uv sync --system` for global installation
- Check Python version compatibility (requires 3.12+)

### Switching Between Environments

```bash
# Deactivate current environment
deactivate

# Activate .venv (recommended)
source .venv/bin/activate

# Activate venv (backup)
source venv/bin/activate
```

## Security notes

- Keep `SUPABASE_SERVICE_ROLE_KEY` secret. In Streamlit it stays server-side, but never print/log it.
- `.streamlit/` is ignored by git in this repo; rotate keys immediately if you ever commit them by accident.

### Recommended setup (single login)

If you want users to only authenticate once (via Supabase):

1. Set the deployed Streamlit app visibility to **Public/Unlisted** (not Private).
2. Use Supabase Auth for sign-in/sign-up (the UI in this repo).

Secrets used:
- `REDIRECT_URL`: where Supabase will redirect after email links (password recovery / verification).
- `ADMIN_EMAILS`: comma-separated list of admin emails (e.g. `"you@example.com,other@example.com"`).
- `SIGNUP_ALLOWLIST_ENABLED`: boolean (`true`/`false`) to require allowlisted emails for signup.
- `SIGNUP_ALLOWLIST_TABLE`: Supabase table name for allowlist (default `signup_allowlist`).
- `PERSIST_LOGIN`: boolean (`true`/`false`) to enable cookie-based session restore (default: `true`).
- `SESSION_ENC_KEY`: Fernet key used to encrypt Supabase tokens before storing them in `app_sessions` (required for persistent login).
- `AUTH_COOKIE_RESTORE_RETRIES`: number of extra cookie-restore reruns during wake-up (default: `2`).
- `AUTH_COOKIE_RESTORE_DELAY_SECONDS`: delay between wake-up restore retries (default: `0.5`).
- `AUTH_EVENT_LOG`: boolean (`true`/`false`) to write structured auth diagnostics (default: `true`).
- `AUTH_EVENT_LOG_PATH`: JSONL file path for auth diagnostics (default: `logs/auth_events.jsonl`).
- `AUTH_EVENT_LOG_DB`: boolean (`true`/`false`) to also persist auth diagnostics to Supabase (default: `false`).
- `AUTH_EVENT_LOG_TABLE`: Supabase table for auth diagnostics (default: `auth_event_logs`).
- `ENV_NAME`: environment tag written with each auth diagnostic row (e.g. `prod`, `staging`).

### Staying logged in (Streamlit Cloud)

Streamlit reruns are normal, but **Streamlit Community Cloud can also restart/sleep** your app process or drop websocket sessions. When that happens, `st.session_state` resets and users can look like they were “logged out”.

This repo uses an **opaque session id (SID)** cookie (via `extra-streamlit-components`) and stores the real Supabase tokens **encrypted server-side** in Supabase (`public.app_sessions`). That way the browser never stores refresh tokens, but the app can still restore sessions after reconnects/restarts.

Setup:
1. Apply the migration `supabase/migrations/20260306_app_sessions.sql`.
2. Add `SESSION_ENC_KEY` to Streamlit secrets. Generate one locally with:
   - `python3 -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"`

Disable persistent login by setting `PERSIST_LOGIN = false`.

### Auth diagnostics log (for hard-to-reproduce wake/logout issues)

When `AUTH_EVENT_LOG` is enabled, the app appends token-safe auth events to `AUTH_EVENT_LOG_PATH`.
This includes whether a cookie was visible, whether session restore succeeded, retry timing, and error type (`invalid_or_expired`, `transient_network`, etc.).

Useful command:
- `tail -f logs/auth_events.jsonl`

For durable production analysis, enable `AUTH_EVENT_LOG_DB=true` and apply migration
`supabase/migrations/20260501_auth_event_logs.sql`.

## Testing persistent login (SID cookie)

Unit tests for the cookie + server-side session store live in `tests/test_persistent_login.py`.

- `pytest -q tests/test_persistent_login.py`
- Included in the full suite: `pytest -q`

These tests use lightweight stubs for Streamlit, cookies, and Supabase admin calls, so they run without network access.
