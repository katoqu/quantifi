import pandas as pd
import pytest


def test_build_export_rows_includes_entries_and_changes():
    """Export builder emits RowType='entry' and RowType='change' rows."""
    from models import build_export_rows

    entry_data = [
        {
            "recorded_at": "2026-02-01T12:00:00Z",
            "value": 80,
            "target_action": "Increase",
            "metrics": {
                "name": "weight",
                "description": "Body mass",
                "unit_name": "kg",
                "unit_type": "float",
                "metric_kind": "quantitative",
                "higher_is_better": False,
                "range_start": None,
                "range_end": None,
                "is_archived": False,
                "categories": {"name": "body"},
            },
        }
    ]
    change_data = [
        {
            "recorded_at": "2026-02-02T12:00:00Z",
            "title": "Started vegetarian nutrition",
            "notes": "No meat",
            "categories": {"name": "health"},
        }
    ]

    rows = build_export_rows(entry_data, change_data)
    row_types = {r["RowType"] for r in rows}
    assert row_types == {"entry", "change"}

    entry_row = next(r for r in rows if r["RowType"] == "entry")
    assert entry_row["Metric"] == "weight"
    assert entry_row["Category"] == "body"
    assert entry_row["Value"] == 80

    change_row = next(r for r in rows if r["RowType"] == "change")
    assert change_row["Title"] == "Started vegetarian nutrition"
    assert change_row["Notes"] == "No meat"
    assert change_row["Category"] == "health"


def test_build_export_rows_preserves_strength_session_payload():
    """Strength-session rows should keep structured workout data in the CSV-friendly export."""
    from models import build_export_rows

    rows = build_export_rows(
        [
            {
                "recorded_at": "2026-02-01T12:00:00Z",
                "value": 80,
                "load_kg": 80,
                "sets": [{"load_kg": 80, "reps": 5}, {"load_kg": 82.5, "reps": 3}],
                "target_action": "Increase",
                "metrics": {
                    "name": "bench",
                    "description": "Bench press",
                    "unit_name": "kg",
                    "unit_type": "float",
                    "metric_kind": "strength_session",
                    "higher_is_better": False,
                    "range_start": None,
                    "range_end": None,
                    "is_archived": False,
                    "categories": {"name": "gym"},
                },
            }
        ],
        [],
    )

    strength_row = next(r for r in rows if r["RowType"] == "entry")
    assert strength_row["Kind"] == "strength_session"
    assert strength_row["LoadKg"] == 80
    assert strength_row["Sets"] == '[{"load_kg": 80, "reps": 5}, {"load_kg": 82.5, "reps": 3}]'


def test_parse_import_frames_backward_compatible_without_rowtype():
    """Importer treats legacy CSVs (no RowType column) as entry-only."""
    from ui.importer import parse_import_frames

    df = pd.DataFrame(
        [
            {
                "Metric": "weight",
                "Value": 80,
                "Date": "2026-02-01 12:00:00",
                "Type": "float",
                "Archived": False,
            }
        ]
    )
    df_entries, df_changes = parse_import_frames(df)
    assert len(df_entries) == 1
    assert len(df_changes) == 0


def test_validate_import_frames_reports_entry_and_change_errors():
    """Importer validation flags invalid entry types and missing change titles."""
    from ui.importer import validate_import_frames

    df_entries = pd.DataFrame(
        [
            {
                "Metric": "weight",
                "Value": 80,
                "Date": "2026-02-01 12:00:00",
                "Type": "not_a_type",
                "Archived": False,
            }
        ]
    )
    df_changes = pd.DataFrame(
        [
            {
                "Title": "",
                "Notes": "x",
                "Date": "2026-02-02 12:00:00",
                "Category": "health",
            }
        ]
    )
    errors = validate_import_frames(df_entries, df_changes)
    assert any("Invalid Type" in e for e in errors)
    assert any("Change Title cannot be empty" in e for e in errors)


def test_validate_import_frames_accepts_strength_session_kind():
    """Importer should treat strength_session as a valid metric kind for round-trip CSV import."""
    from ui.importer import validate_import_frames

    df_entries = pd.DataFrame(
        [
            {
                "Metric": "bench",
                "Value": 80,
                "Date": "2026-02-01 12:00:00",
                "Type": "float",
                "Kind": "strength_session",
                "Archived": False,
                "LoadKg": 80,
                "Sets": '[{"load_kg": 80, "reps": 5}]',
            }
        ]
    )

    errors = validate_import_frames(df_entries, pd.DataFrame())
    assert errors == []

