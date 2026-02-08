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

