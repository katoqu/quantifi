from datetime import datetime, time
from zoneinfo import ZoneInfo
import models
import pandas as pd


USER_TZ = ZoneInfo("Europe/London")

def normalize_name(s: str) -> str:
    return s.strip().lower()

def to_datetz(date):
    return datetime.combine(date, time.min, tzinfo=USER_TZ)

def safe_rerun():
    """Try to trigger a Streamlit rerun if the function exists on the installed version.

    Older Streamlit releases may not expose `st.experimental_rerun`. This helper
    calls it if present and otherwise does nothing (graceful fallback).
    """
    try:
        import streamlit as st
        rerun = getattr(st, "experimental_rerun", None)
        if callable(rerun):
            rerun()
    except Exception:
        # Best-effort only — if rerun isn't available we simply continue.
        return

def format_metric_label(metric, unit_meta):
    """
    Formats a metric name and its unit for display.
    unit_meta: dict of {unit_id: unit_info}
    """

    # Fetch Units 
    unit = unit_meta.get(metric.get("unit_id"))
    unit_display_name = unit.get("name").title() if unit else None

    name = metric.get("name", "Unknown")
    display_name = name.title() if isinstance(name, str) else str(name)


    if unit_display_name:
        return f"{display_name} ({unit_display_name})"
    return display_name

def collect_data(selected_metric, unit_meta):
    # Fetch Units and Metrics
    units = models.get_units() or []
    unit_lookup = {u["id"]: u["name"].title() for u in units}

    mid = selected_metric.get("id")

    unit = unit_meta.get(selected_metric.get("unit_id"))
    m_unit = unit.get("name").title()
    m_name = selected_metric.get("name", "Unknown").title()

    # Fetch Data Entries
    entries = models.get_entries(mid) or []
    if not entries:
        return None, None, None

    # Data Preparation
    dfe = pd.DataFrame(entries)
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    dfe = dfe.sort_values("recorded_at")

    return dfe, m_unit, m_name


