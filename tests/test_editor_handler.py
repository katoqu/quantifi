"""
Comprehensive tests for logic/editor_handler.py - date management and editor state logic.

Tests cover:
- Date range calculations from pill selections
- Date bounds extraction from data
- Conflict detection between filters and unsaved edits
- Change tracking and summary counting
- Editor state synchronization
- State reset operations
- Save operation (create, update, delete processing)
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import pandas as pd
import datetime as dt
import sys

# Add parent directory to path for imports
sys.path.insert(0, '/home/tom/projects/quantifi')

from logic import editor_handler


# Mock Fixtures

@pytest.fixture
def mock_streamlit():
    """Mock Streamlit module."""
    mock_st = Mock()
    mock_st.session_state = {}
    mock_st.error = Mock()
    mock_st.rerun = Mock()
    return mock_st


@pytest.fixture
def sample_dataframe():
    """Sample data entry dataframe."""
    return pd.DataFrame({
        "id": ["e-1", "e-2", "e-3"],
        "recorded_at": pd.to_datetime([
            "2026-03-01 08:00:00",
            "2026-03-02 09:00:00",
            "2026-03-03 10:00:00",
        ], utc=True),
        "value": [72.0, 75.0, 70.0],
        "Change Log": ["", "", ""],
        "Select": [False, False, False],
    })


@pytest.fixture
def mock_utils():
    """Mock utils module."""
    mock = Mock()
    mock.collect_data = Mock(return_value=(None, "unit", "name"))
    mock.finalize_action = Mock()
    return mock


# Tests for get_pill_range

class TestGetPillRange:
    """Tests for date range calculation from pill selections."""

    def test_pill_range_week(self):
        """Should return 7-day range for 'week' selection."""
        end_date = dt.date(2026, 3, 7)
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("Week", abs_min, abs_max)

        assert end == end_date
        assert start == end_date - dt.timedelta(days=7)

    def test_pill_range_month(self):
        """Should return ~31-day range for 'month' selection."""
        end_date = dt.date(2026, 3, 7)
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("Month", abs_min, abs_max)

        assert end == end_date
        assert start == end_date - dt.timedelta(days=31)

    def test_pill_range_year(self):
        """Should return ~365-day range for 'year' selection."""
        end_date = dt.date(2026, 3, 7)
        abs_min = dt.date(2025, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("Year", abs_min, abs_max)

        assert end == end_date
        assert start == end_date - dt.timedelta(days=365)

    def test_pill_range_all_time(self):
        """Should return full date range for 'all time' selection."""
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("All Time", abs_min, abs_max)

        assert start == abs_min
        assert end == abs_max

    def test_pill_range_all_lowercase(self):
        """Should handle 'all' selection."""
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("all", abs_min, abs_max)

        assert start == abs_min
        assert end == abs_max

    def test_pill_range_case_insensitive(self):
        """Should be case-insensitive."""
        end_date = dt.date(2026, 3, 7)
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("WEEK", abs_min, abs_max)

        assert end == end_date
        assert (end - start).days == 7

    def test_pill_range_unknown_selection(self):
        """Should return None for unknown pill selection."""
        abs_min = dt.date(2026, 1, 1)
        abs_max = dt.date(2026, 3, 7)

        start, end = editor_handler.get_pill_range("Invalid", abs_min, abs_max)

        assert start is None
        assert end is None

    def test_pill_range_none_selection(self):
        """Should handle None pill selection."""
        end_date = dt.date(2026, 3, 7)
        abs_min = dt.date(2026, 1, 1)
        
        start, end = editor_handler.get_pill_range(None, abs_min, end_date)
        
        # Should return None, None for invalid selection
        assert start is None
        assert end is None

    def test_pill_range_uses_today_as_default_max(self):
        """Should use today's date when abs_max is None."""
        abs_min = dt.date(2026, 1, 1)
        today = dt.date.today()

        start, end = editor_handler.get_pill_range("Week", abs_min, None)

        assert end == today
        assert (end - start).days == 7

class TestGetDateBounds:
    """Tests for extracting date bounds from dataframe."""

    @patch("logic.editor_handler.st")
    def test_get_date_bounds_initializes_state(self, mock_st, sample_dataframe: pd.DataFrame):
        """Should initialize session state with date bounds."""
        mock_st.session_state = {}

        abs_min, abs_max = editor_handler.get_date_bounds(sample_dataframe, "m-1")

        assert abs_min == dt.date(2026, 3, 1)
        assert abs_max == dt.date(2026, 3, 3)
        assert "prev_date_m-1" in mock_st.session_state

    @patch("logic.editor_handler.st")
    def test_get_date_bounds_converts_to_datetime(self, mock_st, sample_dataframe: pd.DataFrame):
        """Should convert recorded_at to UTC datetime."""
        mock_st.session_state = {}

        abs_min, abs_max = editor_handler.get_date_bounds(sample_dataframe, "m-1")

        # Verify conversion worked
        assert isinstance(abs_min, dt.date)
        assert isinstance(abs_max, dt.date)

    @patch("logic.editor_handler.st")
    def test_get_date_bounds_single_entry(self, mock_st):
        """Should handle dataframe with single entry."""
        mock_st.session_state = {}
        df = pd.DataFrame({
            "recorded_at": pd.to_datetime(["2026-03-05"], utc=True),
        })

        abs_min, abs_max = editor_handler.get_date_bounds(df, "m-1")

        assert abs_min == dt.date(2026, 3, 5)
        assert abs_max == dt.date(2026, 3, 5)

    @patch("logic.editor_handler.st")
    def test_get_date_bounds_preserves_existing_state(self, mock_st, sample_dataframe: pd.DataFrame):
        """Should not overwrite existing baseline state."""
        existing_baseline = (dt.date(2026, 2, 1), dt.date(2026, 2, 28))
        mock_st.session_state = {"prev_date_m-1": existing_baseline}

        abs_min, abs_max = editor_handler.get_date_bounds(sample_dataframe, "m-1")

        # State should remain unchanged
        assert mock_st.session_state["prev_date_m-1"] == existing_baseline


# Tests for has_unsaved_changes

class TestHasUnsavedChanges:
    """Tests for detecting unsaved edits."""

    @patch("logic.editor_handler.st")
    def test_has_unsaved_changes_with_changes(self, mock_st):
        """Should return True when Change Log has markers."""
        df = pd.DataFrame({
            "Change Log": ["", "🔴", "🟡"],  # Has deletion and update markers
        })
        mock_st.session_state = {"draft_state": df}

        result = editor_handler.has_unsaved_changes("draft_state")

        assert result == True

    @patch("logic.editor_handler.st")
    def test_has_unsaved_changes_no_changes(self, mock_st):
        """Should return False when Change Log is empty."""
        df = pd.DataFrame({
            "Change Log": ["", "", ""],
        })
        mock_st.session_state = {"draft_state": df}

        result = editor_handler.has_unsaved_changes("draft_state")

        assert result == False

    @patch("logic.editor_handler.st")
    def test_has_unsaved_changes_missing_state(self, mock_st):
        """Should return False when state key is missing."""
        mock_st.session_state = {}

        result = editor_handler.has_unsaved_changes("nonexistent_state")

        assert result is False

    @patch("logic.editor_handler.st")
    def test_has_unsaved_changes_with_nan_values(self, mock_st):
        """Should handle NaN values in Change Log."""
        df = pd.DataFrame({
            "Change Log": [None, "", "🔴"],  # Has None values
        })
        mock_st.session_state = {"draft_state": df}

        result = editor_handler.has_unsaved_changes("draft_state")

        assert result == True


# Tests for is_date_conflict

class TestIsDateConflict:
    """Tests for detecting filter vs edit conflicts."""

    @patch("logic.editor_handler.has_unsaved_changes")
    @patch("logic.editor_handler.st")
    def test_is_date_conflict_no_conflict(self, mock_st, mock_has_changes):
        """Should return False when filters haven't changed."""
        mock_has_changes.return_value = False
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
            "prev_date_m-1": (dt.date(2026, 3, 1), dt.date(2026, 3, 7)),
            "prev_pill_m-1": "Week",
        }

        result = editor_handler.is_date_conflict("m-1", "draft_state")

        assert result is False

    @patch("logic.editor_handler.has_unsaved_changes")
    @patch("logic.editor_handler.st")
    def test_is_date_conflict_with_unsaved_changes(self, mock_st, mock_has_changes):
        """Should return True when filters changed AND unsaved edits exist."""
        mock_has_changes.return_value = True
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
            "prev_date_m-1": (dt.date(2026, 2, 1), dt.date(2026, 2, 28)),  # Different
            "prev_pill_m-1": "Month",
        }

        result = editor_handler.is_date_conflict("m-1", "draft_state")

        assert result is True

    @patch("logic.editor_handler.has_unsaved_changes")
    @patch("logic.editor_handler.st")
    def test_is_date_conflict_filter_changed_no_edits(self, mock_st, mock_has_changes):
        """Should return False when filters changed but no unsaved edits."""
        mock_has_changes.return_value = False
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
            "prev_date_m-1": (dt.date(2026, 2, 1), dt.date(2026, 2, 28)),
            "prev_pill_m-1": "Month",
        }

        result = editor_handler.is_date_conflict("m-1", "draft_state")

        # Should return False and update baseline
        assert result is False
        # Baseline should be updated to current filter state
        assert mock_st.session_state["prev_date_m-1"] == (
            dt.date(2026, 3, 1),
            dt.date(2026, 3, 7),
        )

    @patch("logic.editor_handler.has_unsaved_changes")
    @patch("logic.editor_handler.st")
    def test_is_date_conflict_missing_keys(self, mock_st, mock_has_changes):
        """Should return False when state keys are missing."""
        mock_has_changes.return_value = False
        mock_st.session_state = {}

        result = editor_handler.is_date_conflict("m-1", "draft_state")

        assert result is False


# Tests for revert_date_range

class TestRevertDateRange:
    """Tests for resetting date picker to baseline."""

    @patch("logic.editor_handler.st")
    def test_revert_date_range_updates_dates(self, mock_st):
        """Should reset date pickers to previous baseline."""
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 5),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
            "prev_date_m-1": (dt.date(2026, 3, 1), dt.date(2026, 3, 4)),
            "prev_pill_m-1": "Custom",
        }

        editor_handler.revert_date_range("m-1")

        assert mock_st.session_state["start_date_m-1"] == dt.date(2026, 3, 1)
        assert mock_st.session_state["end_date_m-1"] == dt.date(2026, 3, 4)
        assert mock_st.session_state["pill_m-1"] == "Custom"

    @patch("logic.editor_handler.st")
    def test_revert_date_range_missing_baseline(self, mock_st):
        """Should handle missing baseline gracefully."""
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 5),
            "end_date_m-1": dt.date(2026, 3, 7),
        }

        # Should not raise exception
        editor_handler.revert_date_range("m-1")


# Tests for sync_editor_changes

class TestSyncEditorChanges:
    """Tests for syncing data_editor changes to draft state."""

    @patch("logic.editor_handler.st")
    def test_sync_editor_changes_updates_values(self, mock_st):
        """Should update draft dataframe with edited values."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "id": ["e-1", "e-2"],
                "value": [72.0, 75.0],
                "Change Log": ["", ""],
            }),
            "editor_widget": {
                "edited_rows": {
                    0: {"value": 73.0},  # Row 0: value changed
                }
            },
        }

        editor_handler.sync_editor_changes(
            "draft_state", "editor_widget", view_df_indices=[0, 1]
        )

        # Draft should be updated
        assert mock_st.session_state["draft_state"].loc[0, "value"] == 73.0

    @patch("logic.editor_handler.st")
    def test_sync_editor_changes_marks_status(self, mock_st):
        """Should update Change Log markers for deletions and edits."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "id": ["e-1", "e-2"],
                "value": [72.0, 75.0],
                "Change Log": ["", ""],
                "Select": [False, False],
            }),
            "editor_widget": {
                "edited_rows": {
                    0: {"Select": True},  # Mark for deletion
                    1: {"value": 80.0},  # Update value
                }
            },
        }

        editor_handler.sync_editor_changes(
            "draft_state", "editor_widget", view_df_indices=[0, 1]
        )

        # Should mark deletions as 🔴 and other changes as 🟡
        assert mock_st.session_state["draft_state"].loc[0, "Change Log"] == "🔴"
        assert mock_st.session_state["draft_state"].loc[1, "Change Log"] == "🟡"

    @patch("logic.editor_handler.st")
    def test_sync_editor_changes_missing_editor_key(self, mock_st):
        """Should handle missing editor key gracefully."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({"id": ["e-1"]}),
        }

        # Should not raise exception
        editor_handler.sync_editor_changes(
            "draft_state", "nonexistent_editor", view_df_indices=[0]
        )


# Tests for get_change_summary

class TestGetChangeSummary:
    """Tests for counting pending changes."""

    @patch("logic.editor_handler.st")
    def test_get_change_summary_deletions(self, mock_st):
        """Should count rows marked for deletion (🔴)."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "Change Log": ["🔴", "", "🔴"],
            }),
            "editor_widget": {"added_rows": []},
        }

        summary = editor_handler.get_change_summary("draft_state", "editor_widget")

        assert summary["del"] == 2
        assert summary["upd"] == 0
        assert summary["add"] == 0

    @patch("logic.editor_handler.st")
    def test_get_change_summary_updates(self, mock_st):
        """Should count rows marked for update (🟡)."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "Change Log": ["🟡", "🟡", ""],
            }),
            "editor_widget": {"added_rows": []},
        }

        summary = editor_handler.get_change_summary("draft_state", "editor_widget")

        assert summary["del"] == 0
        assert summary["upd"] == 2
        assert summary["add"] == 0

    @patch("logic.editor_handler.st")
    def test_get_change_summary_additions(self, mock_st):
        """Should count new rows from data_editor."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({"Change Log": []}),
            "editor_widget": {"added_rows": [{"value": 1}, {"value": 2}, {"value": 3}]},
        }

        summary = editor_handler.get_change_summary("draft_state", "editor_widget")

        assert summary["add"] == 3

    @patch("logic.editor_handler.st")
    def test_get_change_summary_mixed(self, mock_st):
        """Should count all types of changes together."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "Change Log": ["🔴", "🟡", "🟡", ""],
            }),
            "editor_widget": {"added_rows": [{"value": 1}]},
        }

        summary = editor_handler.get_change_summary("draft_state", "editor_widget")

        assert summary["del"] == 1
        assert summary["upd"] == 2
        assert summary["add"] == 1


# Tests for reset_editor_state

class TestResetEditorState:
    """Tests for clearing draft state while preserving structure."""

    @patch("logic.editor_handler.st")
    def test_reset_editor_state_clears_draft(self, mock_st):
        """Should clear draft dataframe but preserve columns."""
        mock_st.session_state = {
            "draft_state": pd.DataFrame({
                "id": ["e-1", "e-2"],
                "recorded_at": [1, 2],
                "value": [72, 75],
                "Change Log": ["🔴", "🟡"],
                "Select": [True, False],
            }),
        }

        editor_handler.reset_editor_state("draft_state", mid="m-1")

        df = mock_st.session_state["draft_state"]
        assert len(df) == 0  # No rows
        assert list(df.columns) == ["id", "recorded_at", "value", "Change Log", "Select"]

    @patch("logic.editor_handler.st")
    def test_reset_editor_state_clears_saved_data(self, mock_st):
        """Should clear saved_data used for visualization."""
        mock_st.session_state = {
            "saved_data_m-1": pd.DataFrame({"value": [72, 75]}),
        }

        editor_handler.reset_editor_state("draft_state", mid="m-1")

        assert len(mock_st.session_state["saved_data_m-1"]) == 0
        assert list(mock_st.session_state["saved_data_m-1"].columns) == [
            "id",
            "recorded_at",
            "value",
            "Change Log",
            "Select",
        ]

    @patch("logic.editor_handler.st")
    def test_reset_editor_state_syncs_baselines(self, mock_st):
        """Should synchronize date baselines to prevent re-triggering conflict warning."""
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }

        editor_handler.reset_editor_state("draft_state", mid="m-1")

        assert mock_st.session_state["prev_date_m-1"] == (
            dt.date(2026, 3, 1),
            dt.date(2026, 3, 7),
        )
        assert mock_st.session_state["prev_pill_m-1"] == "Week"

    @patch("logic.editor_handler.st")
    def test_reset_editor_state_missing_keys(self, mock_st):
        """Should handle missing state keys gracefully."""
        mock_st.session_state = {}

        # Should not raise exception
        editor_handler.reset_editor_state("draft_state", mid="m-1")


# Tests for execute_save

class TestExecuteSave:
    """Tests for committing pending edits to database."""

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_processes_deletions(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should delete entries marked with 🔴."""
        df = pd.DataFrame({
            "id": ["e-1", "e-2", "e-3"],
            "Change Log": ["🔴", "", ""],
            "value": [72.0, 75.0, 70.0],
            "recorded_at": ["2026-03-01", "2026-03-02", "2026-03-03"],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should call delete_entry for e-1
        mock_models.delete_entry.assert_called()
        call_args = [call[0][0] for call in mock_models.delete_entry.call_args_list]
        assert "e-1" in call_args

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_processes_updates(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should update entries marked with 🟡."""
        df = pd.DataFrame({
            "id": ["e-1", "e-2"],
            "Change Log": ["", "🟡"],
            "value": [72.0, 80.0],  # e-2 changed from 75.0
            "recorded_at": ["2026-03-01", "2026-03-02"],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should call update_entry for e-2
        mock_models.update_entry.assert_called()
        call_args = mock_models.update_entry.call_args_list
        assert any("e-2" in str(call) for call in call_args)

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_handles_null_values(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should convert empty/NaN values to None in database."""
        df = pd.DataFrame({
            "id": ["e-1"],
            "Change Log": ["🟡"],
            "value": [None],  # Not measured
            "recorded_at": ["2026-03-01"],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should call update_entry with value=None
        mock_models.update_entry.assert_called()
        update_call = mock_models.update_entry.call_args
        assert update_call[0][1]["value"] is None

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_processes_new_rows(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should create entries from added_rows."""
        df = pd.DataFrame({
            "id": [],
            "Change Log": [],
            "value": [],
            "recorded_at": [],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {
                "added_rows": [
                    {"value": 72.5, "recorded_at": "2026-03-08"},
                    {"value": 73.0, "recorded_at": "2026-03-09"},
                ]
            },
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should call create_entry twice
        assert mock_models.create_entry.call_count == 2

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_preserves_strength_workout_sets(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should persist strength workout sets when editing an existing session row."""
        df = pd.DataFrame({
            "id": ["e-1"],
            "Change Log": ["🟡"],
            "value": [80.0],
            "load_kg": [82.0],
            "sets": ['[{"load_kg": 82.0, "reps": 5}]'],
            "recorded_at": ["2026-03-01"],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        mock_models.update_entry.assert_called_once()
        payload = mock_models.update_entry.call_args[0][1]
        assert payload["value"] == 82.0
        assert payload["load_kg"] == 82.0
        assert payload["sets"] == [{"load_kg": 82.0, "reps": 5}]

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_refreshes_data(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should fetch fresh data after changes and refresh state."""
        df = pd.DataFrame({
            "id": ["e-1"],
            "Change Log": ["🟡"],
            "value": [80.0],
            "recorded_at": ["2026-03-01"],
            "Select": [False],
        })
        fresh_df = pd.DataFrame({
            "id": ["e-1"],
            "Change Log": [""],
            "value": [80.0],
            "recorded_at": ["2026-03-01"],
            "Select": [False],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (fresh_df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should bump cache and call collect_data to refresh data
        mock_cache.bump.assert_called()
        mock_utils.collect_data.assert_called_with({"id": "m-1"})

        # Should call finalize_action to show success message
        mock_utils.finalize_action.assert_called()

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_reruns_ui(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should trigger UI rerun after save completes."""
        df = pd.DataFrame({
            "id": [],
            "Change Log": [],
            "value": [],
            "recorded_at": [],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {"added_rows": []},
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Should call st.rerun()
        mock_st.rerun.assert_called()

    @patch("logic.editor_handler.cache_control")
    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_execute_save_clears_editor_widget_state(self, mock_st, mock_models, mock_utils: Mock, mock_cache: Mock):
        """Should remove data_editor widget state after save."""
        df = pd.DataFrame({
            "id": ["e-1"],
            "Change Log": ["🟡"],
            "value": [80.0],
            "recorded_at": ["2026-03-01"],
            "Select": [False],
        })
        mock_st.session_state = {
            "draft_state": df,
            "editor_widget": {
                "edited_rows": {0: {"value": 81.0}},
                "added_rows": [{"value": 70.0}],
                "deleted_rows": [1],
            },
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }
        mock_utils.collect_data.return_value = (df, "unit", "name")

        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        assert "editor_widget" not in mock_st.session_state


# Integration Tests

class TestIntegration:
    """Integration tests for complete workflows."""

    @patch("logic.editor_handler.st")
    def test_workflow_date_conflict_detection_and_revert(self, mock_st):
        """Test complete workflow: detect conflict and revert dates."""
        # Setup initial state
        mock_st.session_state = {
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
            "prev_date_m-1": (dt.date(2026, 3, 1), dt.date(2026, 3, 7)),
            "prev_pill_m-1": "Week",
            "draft_state": pd.DataFrame({"Change Log": ["🔴"]}),
        }

        with patch.object(editor_handler, "has_unsaved_changes", return_value=True):
            # Change filters
            mock_st.session_state["start_date_m-1"] = dt.date(2026, 2, 1)
            mock_st.session_state["end_date_m-1"] = dt.date(2026, 2, 28)
            mock_st.session_state["pill_m-1"] = "Month"

            # Should detect conflict
            conflict = editor_handler.is_date_conflict("m-1", "draft_state")
            assert conflict is True

            # Revert dates
            editor_handler.revert_date_range("m-1")

            # Dates should be back to original
            assert mock_st.session_state["start_date_m-1"] == dt.date(2026, 3, 1)
            assert mock_st.session_state["end_date_m-1"] == dt.date(2026, 3, 7)

    @patch("logic.editor_handler.utils")
    @patch("logic.editor_handler.models")
    @patch("logic.editor_handler.st")
    def test_workflow_complete_edit_and_save(self, mock_st, mock_models, mock_utils: Mock):
        """Test complete workflow: sync changes and save to database."""
        # Initial state
        df = pd.DataFrame({
            "id": ["e-1", "e-2", "e-3"],
            "recorded_at": ["2026-03-01", "2026-03-02", "2026-03-03"],
            "value": [72.0, 75.0, 70.0],
            "Change Log": ["", "", ""],
            "Select": [False, False, False],
        })
        mock_st.session_state = {
            "draft_state": df.copy(),
            "editor_widget": {
                "edited_rows": {
                    0: {"Select": True},  # Mark e-1 for deletion
                    1: {"value": 80.0},  # Update e-2 value
                }
            },
            "start_date_m-1": dt.date(2026, 3, 1),
            "end_date_m-1": dt.date(2026, 3, 7),
            "pill_m-1": "Week",
        }

        fresh_df = df.copy()
        mock_utils.collect_data.return_value = (fresh_df, "unit", "name")

        # Sync changes
        editor_handler.sync_editor_changes(
            "draft_state", "editor_widget", view_df_indices=[0, 1, 2]
        )

        # Verify changes were synced
        assert mock_st.session_state["draft_state"].loc[0, "Change Log"] == "🔴"
        assert mock_st.session_state["draft_state"].loc[1, "Change Log"] == "🟡"

        # Get summary
        summary = editor_handler.get_change_summary("draft_state", "editor_widget")
        assert summary["del"] == 1
        assert summary["upd"] == 1

        # Save changes
        editor_handler.execute_save("m-1", "draft_state", "editor_widget")

        # Verify database operations were called
        mock_models.delete_entry.assert_called()
        mock_models.update_entry.assert_called()
