# Documentation strategy

For a small personal app, the best strategy is lightweight docs with a clear “home” for each kind of information.

## Where to document what

### `README.md` (project entry point)

Use this for:
- What the app is and what it does
- Quick start (local run)
- Required configuration (secrets, environment)
- Pointers to deeper docs (testing, development notes)

### `docs/TESTING.md` (how to run + extend tests)

Use this for:
- How to run tests locally
- What kinds of tests exist (unit vs UI smoke)
- How to add tests without hitting Supabase/network

### Docstrings + type hints (explain intent at the source)

Use docstrings and type hints for:
- Functions with non-obvious behavior (rounding rules, formatting, defaults)
- Public helpers used across files (`utils.py`, `logic/*`)

Rule of thumb:
- Document **what** and **why** in docstrings.
- Let readable code and naming show **how**.

### Comments (only for “why”, not “what”)

Prefer comments when:
- You’re working around a Streamlit or Supabase quirk
- The code is correct but surprising

If the comment restates the code, delete it.

## Keep docs from drifting

- When you add a feature: add/adjust one short note in `README.md` or a `docs/*` page.
- When you fix a bug: add a regression test and (only if needed) a 1–2 line note in `docs/TESTING.md`.
- If you make a bigger decision (e.g., schema change strategy): add a short “decision note” file (optional) under `docs/decisions/`.

## Suggested next docs (optional)

If the app grows, consider adding:
- `docs/ARCHITECTURE.md`: 1-page overview (modules + data flow)
- `docs/DECISIONS/0001-*.md`: small “ADR-style” notes for important choices
