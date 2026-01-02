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
        st.error(f"⚠️ {error_message}: {str(e)}")
        return None

# --- READ OPERATIONS ---

@st.cache_data(ttl=60)
def get_categories():
    """Fetches all categories for the authenticated user."""
    res = _safe_execute(sb.table("categories").select("*"), "Failed to fetch categories")
    return res.data if res else []

@st.cache_data(ttl=60)
def get_metrics():
    """Fetches all metrics with merged unit metadata."""
    res = _safe_execute(sb.table("metrics").select("*"), "Failed to fetch metrics")
    if res and not res.data:
        get_metrics.clear()
    return res.data if res else []

def get_entries(metric_id=None):
    """Fetches data entries, optionally filtered by metric."""
    query = sb.table("entries").select("*")
    if metric_id:
        query = query.eq("metric_id", metric_id)
    res = _safe_execute(query, "Failed to fetch entries")
    return res.data if res else []

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

def get_metric_by_name(name: str):
    """Finds a metric by name for the current user (case-insensitive)."""
    res = _safe_execute(
        sb.table("metrics").select("*").eq("name", name.lower().strip()),
        "Failed to find metric by name"
    )
    return res.data[0] if res and res.data else None

# --- WRITE OPERATIONS ---

def create_category(name: str):
    return _safe_execute(sb.table("categories").insert({"name": name}), f"Failed to create category")

def create_metric(payload: dict):
    return _safe_execute(sb.table("metrics").insert(payload), "Failed to create metric")

def create_entry(payload: dict):
    return _safe_execute(sb.table("entries").insert(payload), "Failed to save entry")

# --- UPDATE OPERATIONS ---

def update_entry(entry_id, payload: dict):
    return _safe_execute(sb.table("entries").update(payload).eq("id", entry_id), "Failed to update entry")

def update_category(cat_id: str, name: str):
    return _safe_execute(sb.table("categories").update({"name": name}).eq("id", cat_id), "Failed to update category")

def update_metric(metric_id: str, payload: dict):
    return _safe_execute(sb.table("metrics").update(payload).eq("id", metric_id), "Failed to update metric")

# --- DELETE OPERATIONS ---

def delete_entry(entry_id):
    return _safe_execute(sb.table("entries").delete().eq("id", entry_id), "Failed to delete entry")

def delete_metric(metric_id: str):
    return _safe_execute(sb.table("metrics").delete().eq("id", metric_id), "Failed to delete metric")

def delete_category(cat_id: str):
    return _safe_execute(sb.table("categories").delete().eq("id", cat_id), "Failed to delete category")

# --- DATA EXPORT & LIFECYCLE ---

def get_flat_export_data():
    """Fetches flattened dataset for CSV export."""
    query = _safe_execute(
        sb.table("entries").select("recorded_at, value, metrics(name, unit_name, categories(name))"),
        "Failed to fetch export data"
    )
    if not query: return []
    
    rows = []
    for entry in query.data:
        rows.append({
            "Date": entry["recorded_at"],
            "Metric": entry["metrics"]["name"],
            "Value": entry["value"],
            "Unit": entry["metrics"]["unit_name"],
            "Category": entry["metrics"]["categories"]["name"] if entry["metrics"]["categories"] else "None"
        })
    return rows

def wipe_user_data():
    """Wipes all data for the authenticated user in order of dependency."""
    # Note: neq("id", "000...") is a common Supabase trick to bypass 'delete all' protection
    _safe_execute(sb.table("entries").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping entries")
    _safe_execute(sb.table("metrics").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping metrics")
    _safe_execute(sb.table("categories").delete().neq("id", "00000000-0000-0000-0000-000000000000"), "Error wiping categories")

# --- LOCAL BACKUP HELPERS ---

def save_backup_timestamp():
    try:
        data = {"last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
        with open("config.json", "w") as f:
            json.dump(data, f)
    except:
        pass

def get_last_backup_timestamp():
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f).get("last_backup", "Never")
    return "Never"