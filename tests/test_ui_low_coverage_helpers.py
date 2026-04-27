import pytest


pytest.importorskip("streamlit")


def test_metrics_int_or_default_handles_none_and_bad_values():
    """Metrics helper coerces integers and falls back on invalid inputs."""
    from ui import metrics

    assert metrics._int_or_default(None, 7) == 7
    assert metrics._int_or_default("3", 7) == 3
    assert metrics._int_or_default("bad", 7) == 7


def test_metrics_infer_kind_from_unit_type_and_explicit_kind():
    """Metrics helper infers metric_kind from unit_type when missing/invalid."""
    from ui import metrics

    assert metrics._infer_metric_kind({"metric_kind": "count", "unit_type": "float"}) == "count"
    assert metrics._infer_metric_kind({"metric_kind": "nope", "unit_type": "integer"}) == "count"
    assert metrics._infer_metric_kind({"unit_type": "integer_range"}) == "score"
    assert metrics._infer_metric_kind({"unit_type": "float"}) == "quantitative"


def test_metrics_can_convert_kind_only_between_count_and_score():
    """Only score<->count conversions are allowed."""
    from ui import metrics

    assert metrics._can_convert_kind("score", "count") is True
    assert metrics._can_convert_kind("count", "score") is True
    assert metrics._can_convert_kind("score", "quantitative") is False
    assert metrics._can_convert_kind("count", "quantitative") is False
    assert metrics._can_convert_kind("count", "count") is False


def test_metrics_query_matching_tokenizes_and_matches_all_tokens():
    """Search query matching checks name/unit/category token presence."""
    from ui import metrics

    metric = {"name": "sleep quality", "unit_name": "score", "category_id": "c1"}
    cat_labels = {"c1": "Health"}

    assert metrics._metric_matches_query(metric, cat_labels, "") is True
    assert metrics._metric_matches_query(metric, cat_labels, "sleep") is True
    assert metrics._metric_matches_query(metric, cat_labels, "SLEEP (score)") is True
    assert metrics._metric_matches_query(metric, cat_labels, "health score") is True
    assert metrics._metric_matches_query(metric, cat_labels, "health weight") is False


def test_metrics_delete_phrase_matching_requires_delete_prefix():
    """Delete confirmation requires the expected delete phrase."""
    from ui import metrics

    assert metrics._delete_phrase_matches("sleep quality", "delete sleep quality") is True
    assert metrics._delete_phrase_matches("Sleep Quality", " DELETE SLEEP QUALITY ") is True
    assert metrics._delete_phrase_matches("sleep quality", "sleep quality") is False
    assert metrics._delete_phrase_matches("sleep quality", "delete sleep") is False


def test_landing_page_latest_value_formatting_and_kind_inference():
    """Landing page formats latest values based on kind and unit."""
    from ui import landing_page

    metric_q = {"metric_kind": "quantitative", "unit_type": "float", "unit_name": "kg"}
    stats = {"last_date": "01 Feb", "count": 2, "latest": 75.25}
    v, suf = landing_page._format_latest_value(metric=metric_q, stats=stats)
    assert v == "75.2"
    assert suf == " kg"

    metric_score = {"metric_kind": "score", "unit_type": "integer_range", "unit_name": "quality"}
    stats2 = {"last_date": "01 Feb", "count": 1, "latest": 7.7}
    v2, suf2 = landing_page._format_latest_value(metric=metric_score, stats=stats2)
    assert v2 == "8"
    assert suf2 == " quality"

    # No data paths
    v3, suf3 = landing_page._format_latest_value(metric=metric_q, stats={"last_date": "No Data", "count": 0})
    assert v3 == "—" and suf3 == ""


def test_landing_page_sparkline_renders_svg_or_placeholder():
    """Sparkline renders an SVG for data and a placeholder for empty/NaN-only series."""
    from ui import landing_page

    assert "—" in landing_page._render_sparkline([], "#000")
    assert "—" in landing_page._render_sparkline([None, float("nan")], "#000")

    svg = landing_page._render_sparkline([1, 2, 3, 2, 4], "#000", kind="quantitative")
    assert "<svg" in svg and "</svg>" in svg
    assert ("polyline" in svg) or ("line" in svg) or ("circle" in svg)

    # Bounds present should not crash.
    svg2 = landing_page._render_sparkline([1, 2, 3], "#000", kind="score", range_start=0, range_end=10)
    assert "<svg" in svg2 and "</svg>" in svg2


def test_landing_page_extract_latest_target_and_spark_values():
    """Landing page helpers pull target + spark values from entry frames."""
    import pandas as pd
    from ui import landing_page

    df = pd.DataFrame(
        [
            {"recorded_at": "2026-02-01T12:00:00Z", "value": "1", "target_action": None},
            {"recorded_at": "2026-02-02T12:00:00Z", "value": "2.5", "target_action": "Stay"},
            {"recorded_at": "2026-02-03T12:00:00Z", "value": "bad", "target_action": ""},
            {"recorded_at": "2026-02-04T12:00:00Z", "value": "3", "target_action": "Increase"},
        ]
    )
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], utc=True)

    assert landing_page._extract_latest_target(df) == "Increase"
    assert landing_page._compute_spark_values(df, n=3) == [1.0, 2.5, 3.0]


def test_landing_page_select_recent_metrics_excludes_archived_and_sorts():
    """Recent selection excludes archived metrics and sorts newest first."""
    import pandas as pd
    from ui import landing_page

    t0 = pd.Timestamp("2026-02-01T12:00:00Z")
    scored = [
        (t0, {"id": "m1", "is_archived": False}, {"spark_values": []}, None),
        (t0 + pd.Timedelta(days=1), {"id": "m2", "is_archived": True}, {"spark_values": []}, None),
        (t0 + pd.Timedelta(days=2), {"id": "m3", "is_archived": False}, {"spark_values": []}, None),
    ]
    recent = landing_page._select_recent_metrics(scored, limit=5)
    assert [m["id"] for _, m, _, _ in recent] == ["m3", "m1"]


def test_manage_lookups_reconcile_notice_and_create_submit_flow():
    """Category management helpers clear notices and handle create submit paths."""
    from ui import manage_lookups

    # Notice should clear when input changes or is blank.
    notice, notice_name = manage_lookups._reconcile_create_notice("exists", "health", "Health")
    assert notice == "exists"
    notice, notice_name = manage_lookups._reconcile_create_notice("exists", "health", "Fitness")
    assert notice is None and notice_name is None
    notice, notice_name = manage_lookups._reconcile_create_notice("exists", "health", "")
    assert notice is None and notice_name is None

    # Create flow: empty
    created = []

    def _get_by_name(name):
        return next((c for c in created if c["name"] == name), None)

    def _create(name):
        created.append({"id": f"id_{name}", "name": name})

    res = manage_lookups._handle_create_category_submit(
        new_cat_name="   ", get_category_by_name=_get_by_name, create_category=_create
    )
    assert res["status"] == "empty"

    # Create flow: new
    res = manage_lookups._handle_create_category_submit(
        new_cat_name="Health", get_category_by_name=_get_by_name, create_category=_create
    )
    assert res["status"] == "created"
    assert res["norm_name"] == "health"
    assert res["created"]["id"] == "id_health"

    # Create flow: exists
    res = manage_lookups._handle_create_category_submit(
        new_cat_name="health", get_category_by_name=_get_by_name, create_category=_create
    )
    assert res["status"] == "exists"
    assert res["existing"]["id"] == "id_health"


def test_metrics_search_label_includes_category_and_formatted_metric(monkeypatch):
    """Metric search label includes category label and formatted metric label."""
    from ui import metrics

    monkeypatch.setattr(metrics.utils, "format_metric_label", lambda m: "Sleep (Quality)")
    out = metrics._metric_search_label({"category_id": "c1"}, {"c1": "Health"})
    assert out == "Health • Sleep (Quality)"
