from datetime import datetime, time
from zoneinfo import ZoneInfo

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
