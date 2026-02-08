# Testing

This project uses `pytest` for a small, fast test suite that helps prevent regressions as the app grows.

## Goals

- Catch regressions in *logic* (formatting, rounding, defaults) quickly.
- Provide a minimal “UI smoke test” to ensure key pages still render.
- Avoid any real network/Supabase calls during tests.

## Quick start

```bash
python3 -m pip install -r requirements.txt
python3 -m pytest
```

## How tests are structured

| Area | What to test | Where |
|---|---|---|
| Pure helpers | formatting, rounding, labeling | `tests/test_capture_helpers.py`, `tests/test_utils.py` |
| Data semantics | “not measured” vs `0` behavior | `tests/test_visualize_stats.py` |
| UI smoke | page renders without crashing | `tests/test_pages_smoke.py` |

### Current tests (overview)

| File | Test | Purpose |
|---|---|---|
| `tests/test_capture_helpers.py` | `test_infer_float_step_and_format_integer` | Integer input → step/format are correct. |
| `tests/test_capture_helpers.py` | `test_infer_float_step_and_format_decimal` | Decimal input → step/format are correct. |
| `tests/test_capture_helpers.py` | `test_round_down_respects_decimals` | Rounding-down behaves as expected. |
| `tests/test_capture_helpers.py` | `test_infer_from_history_returns_reasonable_step` | History-based step inference returns a positive step and a format. |
| `tests/test_utils.py` | `test_normalize_name_strips_and_lowercases` | Name normalization is stable. |
| `tests/test_utils.py` | `test_format_metric_label_includes_unit_and_archived` | Label includes unit and archived marker. |
| `tests/test_utils.py` | `test_to_datetz_midday` | Date → midday datetime conversion. |
| `tests/test_pages_smoke.py` | `test_tracker_page_renders_overview` | `tracker_page()` runs in Streamlit AppTest with DB calls mocked. |
| `tests/test_visualize_stats.py` | `test_get_metric_stats_excludes_not_measured_but_keeps_zero` | NULL/blank values don’t affect aggregates; numeric `0` remains a valid measurement. |
| `tests/test_visualize_stats.py` | `test_get_metric_stats_all_not_measured_returns_no_data` | All-NULL/blank series reports “No Data” (not zero). |

## Running tests

- All tests: `python3 -m pytest`
- One file: `python3 -m pytest tests/test_utils.py`
- Metric stats semantics: `python3 -m pytest tests/test_visualize_stats.py`
- One test: `python3 -m pytest -k to_datetz_midday`

## Patterns used in this repo

### 1) Prefer unit tests for helper logic

If a function is deterministic and doesn’t require Streamlit rendering, test it directly. These tests are fast and rarely flaky.

### 2) Mock the data layer in UI tests

UI/controller functions often call `models.*` functions that talk to Supabase. In tests, replace those calls with fakes:

- `monkeypatch.setattr(pages.models, "get_metrics", lambda ...: [...])`
- `monkeypatch.setattr(pages.models, "get_all_entries_bulk", lambda: [])`

This keeps tests offline and predictable.

### 3) Streamlit UI smoke tests (minimal expectations)

Use `streamlit.testing.v1.AppTest` for a “does it render” check. These tests intentionally avoid pixel-perfect assertions.

## Adding a new test (recommended workflow)

1. When you add a feature, identify the most stable “core logic” and add a unit test for it first.
2. When you fix a bug, add a regression test that fails without the fix.
3. Keep UI tests minimal:
   - assert “no exception” and/or basic state routing
   - mock data access

## Notes / troubleshooting

- Some Streamlit warnings about `ScriptRunContext` can show up under test runners; smoke tests are written to tolerate this.
- `pytest.ini` filters a known Supabase `gotrue` deprecation warning to keep output readable.
