"""
Comprehensive tests for models.py - database operations and data retrieval logic.

Tests cover:
- Data fetching operations with Supabase mocking
- Error handling via _safe_execute wrapper
- Query filtering and sorting
- Data transformation logic
- Lookups by name
- Data bounds and statistics
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
import sys
import importlib
import models
import os


@pytest.fixture(autouse=True)
def reset_models_module():
    """Reset models module before each test to clear any stale patches."""
    # Reload models to ensure clean state
    importlib.reload(models)
    yield
    # Reload again after test to prevent cross-test pollution
    importlib.reload(models)


# Mock Data Fixtures
@pytest.fixture
def mock_sb():
    """Mock Supabase client."""
    return Mock()


@pytest.fixture
def mock_session_state():
    """Mock Streamlit session state."""
    return {"user": Mock(id="test-user-123")}


@pytest.fixture
def sample_categories():
    return [
        {"id": "cat-1", "name": "health"},
        {"id": "cat-2", "name": "fitness"},
        {"id": "cat-3", "name": "nutrition"},
    ]


@pytest.fixture
def sample_metrics():
    return [
        {"id": "m-1", "name": "heart_rate", "unit_name": "bpm", "is_archived": False},
        {"id": "m-2", "name": "weight", "unit_name": "kg", "is_archived": False},
        {"id": "m-3", "name": "old_metric", "unit_name": "units", "is_archived": True},
    ]


@pytest.fixture
def sample_entries():
    return [
        {"id": "e-1", "metric_id": "m-1", "value": 72.5, "recorded_at": "2026-03-07T08:00:00Z"},
        {"id": "e-2", "metric_id": "m-1", "value": 75.0, "recorded_at": "2026-03-07T09:00:00Z"},
        {"id": "e-3", "metric_id": "m-1", "value": None, "recorded_at": "2026-03-07T10:00:00Z"},
    ]


@pytest.fixture
def sample_change_events():
    return [
        {
            "id": "ce-1",
            "title": "Started exercise",
            "notes": "Morning run",
            "recorded_at": "2026-03-07T06:00:00Z",
            "created_at": "2026-03-07T07:00:00Z",
            "category_id": "cat-2",
            "categories": {"name": "fitness"},
        },
        {
            "id": "ce-2",
            "title": "Diet change",
            "notes": "Increased protein",
            "recorded_at": "2026-03-06T12:00:00Z",
            "created_at": "2026-03-06T12:30:00Z",
            "category_id": "cat-3",
            "categories": {"name": "nutrition"},
        },
    ]


# Tests for Helper Wrapper

class TestSafeExecute:
    """Tests for _safe_execute error handling wrapper."""

    @patch("models.st")
    def test_safe_execute_success(self, mock_st):
        """Should execute query and return result on success."""
        mock_query = Mock()
        mock_result = Mock(data=[{"id": "1"}])
        mock_query.execute.return_value = mock_result

        result = models._safe_execute(mock_query, "Test error")
        assert result == mock_result
        mock_query.execute.assert_called_once()

    @patch("models.st")
    def test_safe_execute_ignores_jwt_errors(self, mock_st):
        """Should silently ignore JWT-related errors."""
        mock_query = Mock()
        mock_query.execute.side_effect = Exception("jwt_expired")

        result = models._safe_execute(mock_query, "Auth failed")
        assert result is None
        # st.error should NOT be called for JWT errors
        mock_st.error.assert_not_called()

    @patch("models.st")
    def test_safe_execute_shows_other_errors(self, mock_st):
        """Should show error message for non-JWT exceptions."""
        mock_query = Mock()
        mock_query.execute.side_effect = Exception("Connection timeout")

        result = models._safe_execute(mock_query, "Network failed")
        assert result is None
        # st.error should be called for non-JWT errors
        mock_st.error.assert_called_once()
        assert "Network failed" in str(mock_st.error.call_args)


# Tests for Current User ID

class TestCurrentUserId:
    """Tests for _current_user_id helper."""

    @patch("models.st")
    def test_current_user_id_with_user(self, mock_st):
        """Should return user ID from session state."""
        mock_user = Mock(id="user-123")
        mock_st.session_state = {"user": mock_user}

        user_id = models._current_user_id()
        assert user_id == "user-123"

    @patch("models.st")
    def test_current_user_id_without_user(self, mock_st):
        """Should return 'anon' when user is not in session."""
        mock_st.session_state = {}

        user_id = models._current_user_id()
        assert user_id == "anon"

    @patch("models.st")
    def test_current_user_id_with_none_id(self, mock_st):
        """Should handle user with None ID."""
        mock_user = Mock(id=None)
        mock_st.session_state = {"user": mock_user}

        user_id = models._current_user_id()
        # Should return 'anon' when user.id is None
        assert user_id == "anon"


# Tests for Read Operations

class TestGetMetrics:
    """Tests for get_metrics operations."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_metrics_excludes_archived(self, mock_st, mock_cache):
        """Should filter out archived metrics by default."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_metrics_cached") as mock_cached:
            mock_cached.return_value = [{"id": "m-1", "is_archived": False}]

            result = models.get_metrics(include_archived=False)

            assert result == [{"id": "m-1", "is_archived": False}]
            mock_cached.assert_called_once()

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_metrics_includes_archived_when_requested(self, mock_st, mock_cache):
        """Should include archived metrics when explicitly requested."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_metrics_cached") as mock_cached:
            mock_cached.return_value = [{"id": "m-1", "is_archived": True}]

            result = models.get_metrics(include_archived=True)

            assert result == [{"id": "m-1", "is_archived": True}]

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_metrics_handles_empty_result(self, mock_st, mock_cache):
        """Should return empty list when no metrics found."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_metrics_cached") as mock_cached:
            mock_cached.return_value = []

            result = models.get_metrics()

            assert result == []


class TestGetCategories:
    """Tests for get_categories wrapper."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_categories_returns_cached(self, mock_st, mock_cache):
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_categories_cached") as mock_cached:
            mock_cached.return_value = [{"id": "cat-1", "name": "health"}]

            result = models.get_categories()

            assert result == [{"id": "cat-1", "name": "health"}]
            mock_cached.assert_called_once()


class TestGetEntries:
    """Tests for get_entries operations."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_entries_by_metric_id(self, mock_st, mock_cache):
        """Should filter entries by metric_id."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_entries_cached") as mock_cached:
            mock_result = Mock(
                data=[
                    {"id": "e-1", "metric_id": "m-1", "value": 72.5},
                    {"id": "e-2", "metric_id": "m-1", "value": 75.0},
                ]
            )
            mock_cached.return_value = mock_result.data

            result = models.get_entries(metric_id="m-1")

            assert len(result) == 2
            assert all(e["metric_id"] == "m-1" for e in result)

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_entries_unfiltered(self, mock_st, mock_cache):
        """Should return all entries when no metric_id specified."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(
                data=[
                    {"id": "e-1", "metric_id": "m-1", "value": 72},
                    {"id": "e-2", "metric_id": "m-2", "value": 80},
                ]
            )
            mock_safe.return_value = mock_result

            result = models.get_entries()

            assert len(result) == 2


class TestGetChangeEvents:
    """Tests for change event retrieval."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_change_events_returns_newest_first(self, mock_st, mock_cache, sample_change_events):
        """Should return events ordered by recorded_at (newest first)."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_change_events_cached") as mock_cached:
            mock_cached.return_value = sample_change_events

            result = models.get_change_events(limit=200)

            # Should be ordered by recorded_at descending
            assert len(result) == 2
            assert result[0]["recorded_at"] > result[1]["recorded_at"]

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_change_events_respects_limit(self, mock_st, mock_cache):
        """Should respect the limit parameter."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_change_events_cached") as mock_cached:
            mock_cached.return_value = [{"id": "ce-1"}]

            models.get_change_events(limit=50)

            # Verify _get_change_events_cached was called with correct limit
            mock_cached.assert_called_once()


# Tests for Lookup Operations

class TestLookupByName:
    """Tests for finding metrics and categories by name."""

    @patch("models.st")
    def test_get_metric_by_name_case_insensitive(self, mock_st):
        """Should find metric by name case-insensitively."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(data=[{"id": "m-1", "name": "heart_rate"}])
            mock_safe.return_value = mock_result

            result = models.get_metric_by_name("HEART_RATE")

            assert result == {"id": "m-1", "name": "heart_rate"}

    @patch("models.st")
    def test_get_metric_by_name_strips_whitespace(self, mock_st):
        """Should strip whitespace from name lookup."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(data=[{"id": "m-2", "name": "weight"}])
            mock_safe.return_value = mock_result

            result = models.get_metric_by_name("  WEIGHT  ")

            assert result == {"id": "m-2", "name": "weight"}

    @patch("models.st")
    def test_get_metric_by_name_not_found(self, mock_st):
        """Should return None when metric not found."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(data=[])
            mock_safe.return_value = mock_result

            result = models.get_metric_by_name("nonexistent")

            assert result is None

    @patch("models.st")
    def test_get_category_by_name(self, mock_st):
        """Should find category by name case-insensitively."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(data=[{"id": "cat-1", "name": "fitness"}])
            mock_safe.return_value = mock_result

            result = models.get_category_by_name("FITNESS")

            assert result == {"id": "cat-1", "name": "fitness"}


# Tests for Data Statistics

class TestDataStatistics:
    """Tests for data bounds and statistics operations."""

    @patch("models.st")
    def test_get_metric_value_bounds(self, mock_st):
        """Should return min and max values for a metric."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(
                data=[{"value": 72.5}, {"value": 80.0}, {"value": 68.0}]
            )
            mock_safe.return_value = mock_result

            min_val, max_val = models.get_metric_value_bounds("m-1")

            assert min_val == 68.0
            assert max_val == 80.0

    @patch("models.st")
    def test_get_metric_value_bounds_empty(self, mock_st):
        """Should return None, None for metric with no entries."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(data=[])
            mock_safe.return_value = mock_result

            min_val, max_val = models.get_metric_value_bounds("m-1")

            assert min_val is None
            assert max_val is None

    @patch("models.st")
    def test_get_entry_count(self, mock_st):
        """Should return exact count of entries for a metric."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(count=42)
            mock_safe.return_value = mock_result

            count = models.get_entry_count("m-1")

            assert count == 42

    @patch("models.st")
    def test_get_entry_count_zero(self, mock_st):
        """Should return 0 for metric with no entries."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_safe.return_value = None

            count = models.get_entry_count("m-1")

            assert count == 0

    @patch("models.st")
    def test_metric_has_fractional_values_true(self, mock_st):
        """Should detect fractional values in metric data."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(
                data=[
                    {"value": 72.5},  # Fractional
                    {"value": 70},
                ]
            )
            mock_safe.return_value = mock_result

            has_fractional = models.metric_has_fractional_values("m-1")

            assert has_fractional is True

    @patch("models.st")
    def test_metric_has_fractional_values_false(self, mock_st):
        """Should return False for integer-only metrics."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(
                data=[
                    {"value": 72},
                    {"value": 70},
                    {"value": 75},
                ]
            )
            mock_safe.return_value = mock_result

            has_fractional = models.metric_has_fractional_values("m-1")

            assert has_fractional is False

    @patch("models.st")
    def test_metric_has_fractional_values_handles_invalid(self, mock_st):
        """Should skip non-numeric values gracefully."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(
                data=[
                    {"value": "invalid"},
                    {"value": 72.5},  # Valid fractional
                    {"value": None},
                ]
            )
            mock_safe.return_value = mock_result

            has_fractional = models.metric_has_fractional_values("m-1")

            assert has_fractional is True


class TestGetCategoryUsage:
    """Tests for category usage counting."""

    @patch("models.st")
    def test_get_category_usage_count(self, mock_st):
        """Should return count of active metrics in a category."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(count=5)
            mock_safe.return_value = mock_result

            count = models.get_category_usage_count("cat-1")

            assert count == 5

    @patch("models.st")
    def test_get_category_usage_count_zero(self, mock_st):
        """Should return 0 when category has no active metrics."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_result = Mock(count=0)
            mock_safe.return_value = mock_result

            count = models.get_category_usage_count("cat-1")

            assert count == 0


class TestRecentValues:
    """Tests for retrieving recent numeric values."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_recent_numeric_values_filters_nonnumeric(self, mock_st, mock_cache):
        """Should filter out non-numeric values."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_recent_numeric_values_cached") as mock_cached:
            # Return values in oldest->newest order (already reversed by the mock)
            mock_cached.return_value = [70.0, 75.0]

            values = models.get_recent_numeric_values("m-1", limit=10)

            # Should only contain numeric values (70.0 and 75.0)
            assert len(values) == 2
            assert 70.0 in values
            assert 75.0 in values

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_recent_numeric_values_empty(self, mock_st, mock_cache):
        """Should return empty list for metric with no values."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_recent_numeric_values_cached") as mock_cached:
            mock_cached.return_value = []

            values = models.get_recent_numeric_values("m-1")

            assert values == []


# Tests for Latest Entry

class TestLatestEntry:
    """Tests for retrieving the most recent entry."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_latest_entry_only(self, mock_st, mock_cache):
        """Should return only the most recent entry."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_latest_entry_only_cached") as mock_cached:
            mock_cached.return_value = {"id": "e-latest", "value": 75.0}

            result = models.get_latest_entry_only("m-1")

            assert result == {"id": "e-latest", "value": 75.0}

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_latest_entry_none(self, mock_st, mock_cache):
        """Should return None when no entries exist."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_latest_entry_only_cached") as mock_cached:
            mock_cached.return_value = None

            result = models.get_latest_entry_only("m-1")

            assert result is None


# Tests for Write Operations

class TestWriteOperations:
    """Tests for create, update, and delete operations."""

    @patch("models.st")
    def test_create_category(self, mock_st):
        """Should call insert with category payload."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.create_category("Health")

            # Verify _safe_execute was called once
            assert mock_safe.call_count == 1

    @patch("models.st")
    def test_create_metric(self, mock_st):
        """Should create metric with provided payload."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            payload = {"name": "heart_rate", "unit_name": "bpm"}
            models.create_metric(payload)

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_create_entry(self, mock_st):
        """Should create entry with provided payload."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            payload = {"metric_id": "m-1", "value": 72.5, "recorded_at": "2026-03-07"}
            models.create_entry(payload)

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_update_entry(self, mock_st):
        """Should update entry with provided payload."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.update_entry("e-1", {"value": 75.0})

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_update_category(self, mock_st):
        """Should update category name."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.update_category("cat-1", "Updated Name")

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_delete_entry(self, mock_st):
        """Should delete entry by id."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.delete_entry("e-1")

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_delete_metric(self, mock_st):
        """Should delete metric by id."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.delete_metric("m-1")

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_delete_category(self, mock_st):
        """Should delete category by id."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.delete_category("cat-1")

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_create_change_event(self, mock_st):
        """Should create change event with provided payload."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            payload = {
                "title": "Started exercise",
                "notes": "Morning run",
                "category_id": "cat-2",
            }
            models.create_change_event(payload)

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_update_change_event(self, mock_st):
        """Should update change event."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.update_change_event("ce-1", {"title": "Updated title"})

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_delete_change_event(self, mock_st):
        """Should delete change event by id."""
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.delete_change_event("ce-1")

            mock_safe.assert_called_once()


# Tests for All Entries Bulk Operation

class TestBulkOperations:
    """Tests for bulk data operations."""

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_all_entries_bulk_excludes_archived_metrics(self, mock_st, mock_cache):
        """Should fetch entries only from non-archived metrics."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_all_entries_bulk_cached") as mock_cached:
            mock_cached.return_value = [
                {"id": "e-1", "metric_id": "m-1", "value": 72},
                {"id": "e-2", "metric_id": "m-2", "value": 80},
            ]

            result = models.get_all_entries_bulk()

            assert result is not None
            assert len(result) == 2

    @patch("models.cache_control")
    @patch("models.st")
    def test_get_all_entries_bulk_handles_none(self, mock_st, mock_cache):
        """Should return None to prevent showing '0 entries' flash."""
        mock_cache.get_buster.return_value = 0
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_get_all_entries_bulk_cached") as mock_cached:
            mock_cached.return_value = None

            result = models.get_all_entries_bulk()

            assert result is None


class TestExportHelpers:
    """Tests for export helpers that touch Supabase and local disk."""

    @patch("models.st")
    def test_get_flat_export_data_returns_empty_on_missing_entries(self, mock_st):
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_safe.return_value = None

            result = models.get_flat_export_data()

            assert result == []

    @patch("models.st")
    def test_get_flat_export_data_builds_rows(self, mock_st):
        mock_st.session_state = {"user": Mock(id="u-1")}

        entries_res = Mock(data=[{"recorded_at": "2026-03-07T08:00:00Z", "value": 1, "metrics": {}}])
        changes_res = Mock(data=[{"recorded_at": "2026-03-07T09:00:00Z", "title": "x", "notes": ""}])

        with patch.object(models, "_safe_execute") as mock_safe:
            mock_safe.side_effect = [entries_res, changes_res]
            with patch.object(models, "build_export_rows") as mock_build:
                mock_build.return_value = [{"RowType": "entry"}]

                result = models.get_flat_export_data()

                assert result == [{"RowType": "entry"}]
                mock_build.assert_called_once()

    @patch("models.st")
    def test_wipe_user_data_calls_safe_execute(self, mock_st):
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.wipe_user_data()

            assert mock_safe.call_count == 4

    @patch("models.st")
    def test_archive_metric_calls_safe_execute(self, mock_st):
        mock_st.session_state = {"user": Mock(id="u-1")}

        with patch.object(models, "_safe_execute") as mock_safe:
            models.archive_metric("m-1")

            mock_safe.assert_called_once()

    @patch("models.st")
    def test_save_and_load_backup_timestamp(self, mock_st, tmp_path, monkeypatch):
        mock_st.session_state = {"user": Mock(id="u-1")}
        monkeypatch.chdir(tmp_path)

        models.save_backup_timestamp()
        assert os.path.exists("config.json") is True

        last = models.get_last_backup_timestamp()
        assert isinstance(last, str)
        assert last != "Never"

    @patch("models.st")
    def test_get_last_backup_timestamp_missing_file(self, mock_st, tmp_path, monkeypatch):
        mock_st.session_state = {"user": Mock(id="u-1")}
        monkeypatch.chdir(tmp_path)

        assert models.get_last_backup_timestamp() == "Never"
