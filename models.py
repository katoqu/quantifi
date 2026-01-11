from supabase_config import sb
import streamlit as st
import json
import os
from datetime import datetime

# --- HELPER ERROR WRAPPER ---
def _safe_execute(query_func, error_message="Database operation failed"):
    """Internal helper to catch Supabase/Network errors."""
    try:
        return query_func.execute()
    except Exception as e:
        # Ignore JWT/Auth errors during initial startup
        if "jwt" not in str(e).lower():
            st.error(f"⚠️ {error_message}: {str(e)}")
        return None

# --- READ OPERATIONS ---

@st.cache_data(ttl=60)
def get_categories():
    """Fetches all categories for the authenticated user."""
    res = _safe_execute(sb.table("categories").select("*"), "Failed to fetch categories")
    return res.data if res else []

@st.cache_data(ttl=60)
def get_metrics(include_archived=False):
    """Fetches metrics, filtering archived ones by default for speed."""
    query = sb.table("metrics").select("*")
    if not include_archived:
        query = query.eq("is_archived", False)
    res = _safe_execute(query, "Failed to fetch metrics")
    return res.data if res else []

def get_entries(metric_id=None):
    """Fetches data entries, optionally filtered by metric."""
    query = sb.table("entries").select("*")
    if metric_id:
        query = query.eq("metric_id", metric_id)
    res = _safe_execute(query, "Failed to fetch entries")
    return res.data if res else []

def get_metric_by_name(name: str):
    """
    Finds a metric by name for the current user (case-insensitive).
    Required by the importer to prevent duplicate metric creation.
    """
    res = _safe_execute(
        sb.table("metrics").select("*").eq("name", name.lower().strip()),
        "Failed to find metric by name"
    )
    return res.data[0] if res and res.data else None

def get_metric_value_bounds(metric_id: str):
    """
    Returns the min and max values currently recorded for a metric.
    Prevents range changes in metrics.py that would invalidate existing data.
    """
    res = _safe_execute(
        sb.table("entries")
        .select("value")
        .eq("metric_id", metric_id),
        "Failed to fetch value bounds"
    )
    if res and res.data:
        values = [float(row['value']) for row in res.data]
        return min(values), max(values)
    return None, None

def get_entry_count(metric_id: str):
    """Returns the total number of entries for a specific metric."""
    res = _safe_execute(
        sb.table("entries").select("id", count="exact").eq("metric_id", metric_id),
        "Failed to count entries"
    )
    return res.count if res and res.count is not None else 0

def get_category_by_name(name: str):
    """Finds a category by name for the current user (case-insensitive)."""
    res = _safe_execute(
        sb.table("categories").select("*").eq("name", name.lower().strip()),
        "Failed to find category by name"
    )
    return res.data[0] if res and res.data else None

@st.cache_data(ttl=120)
def get_all_entries_bulk():
    res = _safe_execute(
        sb.table("entries")
        .select("*, metrics!inner(is_archived)")
        .eq("metrics.is_archived", False), 
        "Bulk fetch failed"
    )
    if res is None:
        return None  # Prevents showing '0 entries' flash
    return res.data

@st.cache_data(ttl=30) # Short TTL for active recording
def get_latest_entry_only(metric_id):
    """Fetches ONLY the single most recent record for smart defaults."""
    res = _safe_execute(
        sb.table("entries")
        .select("*")
        .eq("metric_id", metric_id)
        .order("recorded_at", desc=True)
        .limit(1), 
        "Failed to fetch latest entry"
    )
    return res.data[0] if res and res.data else None

# --- WRITE OPERATIONS ---

def create_category(name: str):
    return _safe_execute(sb.table("categories").insert({"name": name}), "Failed to create category")

def create_metric(payload: dict):
    return _safe_execute(sb.table("metrics").insert(payload), "Failed to create metric")

def create_entry(payload: dict):
    return _safe_execute(sb.table("entries").insert(payload), "Failed to save entry")

# --- UPDATE OPERATIONS ---

def update_entry(entry_id, payload: dict):
    return _safe_execute(sb.table("entries").update(payload).eq("id", entry_id), "Failed to update entry")

def update_category(cat_id: str, name: str):
    """UPDATED: Re-added missing attribute to fix category rename errors."""
    return _safe_execute(sb.table("categories").update({"name": name}).eq("id", cat_id), "Failed to update category")

def update_metric(metric_id: str, payload: dict):
    return _safe_execute(sb.table("metrics").update(payload).eq("id", metric_id), "Failed to update metric")

# --- DELETE OPERATIONS ---

def delete_entry(entry_id):
    return _safe_execute(sb.table("entries").delete().eq("id", entry_id), "Failed to delete entry")

def delete_metric(metric_id: str):
    return _safe_execute(sb.table("metrics").delete().eq("id", metric_id), "Failed to delete metric")

def delete_category(cat_id: str):
    """UPDATED: Added for complete category management capability."""
    return _safe_execute(sb.table("categories").delete().eq("id", cat_id), "Failed to delete category")

# --- DATA EXPORT & LIFECYCLE ---

def get_flat_export_data():
    """
    MODIFIED: Fetches flattened dataset including metric metadata 
    (Type, Min, Max) for a complete round-trip backup.
    """
    # 1. Update query to include metadata columns from the metrics table
    query = _safe_execute(
        sb.table("entries").select(
            "recorded_at, value, metrics(name, description, unit_name, unit_type, range_start, range_end, categories(name))"
        ),
        "Failed to fetch export data"
    )
    if not query: return []
    
    rows = []
    for entry in query.data:
        import pandas as pd
        ts = pd.to_datetime(entry["recorded_at"], format='ISO8601', utc=True)
        
        # 2. Append the new metadata keys matching the new importer expectations
        rows.append({
            "Date": ts.strftime('%Y-%m-%d %H:%M:%S'),
            "Metric": entry["metrics"]["name"],
            "Description": entry["metrics"].get("description", ""),
            "Value": entry["value"],
            "Unit": entry["metrics"]["unit_name"],
            "Category": entry["metrics"]["categories"]["name"] if entry["metrics"]["categories"] else "None",
            "Type": entry["metrics"]["unit_type"],
            "Min": entry["metrics"]["range_start"],
            "Max": entry["metrics"]["range_end"]
        })
    return rows

def wipe_user_data():
    """Wipes all data for the authenticated user."""
    _safe_execute(sb.table("entries").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping entries")
    _safe_execute(sb.table("metrics").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping metrics")
    _safe_execute(sb.table("categories").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping categories")


def archive_metric(metric_id: str):
    """Soft-deletes a metric by setting the archive flag."""
    return _safe_execute(
        sb.table("metrics").update({"is_archived": True}).eq("id", metric_id),
        "Failed to archive metric"
    )

# --- LOCAL BACKUP HELPERS (Restored) ---

def save_backup_timestamp():
    """Saves the current timestamp to a local config file."""
    try:
        data = {"last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open("config.json", "w") as f:
            json.dump(data, f)
    except:
        pass

def get_last_backup_timestamp():
    """Retrieves the last recorded backup timestamp from local storage."""
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f).get("last_backup", "Never")
    return "Never"