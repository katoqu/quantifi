from supabase_config import sb
import streamlit as st
import json
import os
from datetime import datetime

@st.cache_data(ttl=60)
def get_categories():
    response = sb.table("categories").select("*").execute()
    return response.data

@st.cache_data(ttl=60)
def get_metrics():
    # Now returns name, unit_name, unit_type, range_start, and range_end directly
    response = sb.table("metrics").select("*").execute()
    if not response.data:
        get_metrics.clear()
    return response.data

def get_entries(metric_id=None):
    query = sb.table("entries").select("*")
    if metric_id:
        query = query.eq("metric_id", metric_id)
    response = query.execute()
    return response.data

def create_category(name: str):
    return sb.table("categories").insert({"name": name}).execute()

def create_metric(payload: dict):
    # Payload now includes: name, unit_name, unit_type, range_start, range_end
    return sb.table("metrics").insert(payload).execute()

def create_entry(payload: dict):
    return sb.table("entries").insert(payload).execute()

def update_entry(entry_id, payload: dict):
    return sb.table("entries").update(payload).eq("id", entry_id).execute()

def delete_entry(entry_id):
    return sb.table("entries").delete().eq("id", entry_id).execute()

def update_category(cat_id: str, name: str):
    """Updates the name of an existing category."""
    return sb.table("categories").update({"name": name}).eq("id", cat_id).execute()

def update_metric(metric_id: str, payload: dict):
    """Updates metric metadata (name, unit_name, category, etc.)."""
    return sb.table("metrics").update(payload).eq("id", metric_id).execute()

def get_entry_count(metric_id: str):
    """Checks how many entries exist for a specific metric."""
    response = sb.table("entries").select("id", count="exact").eq("metric_id", metric_id).execute()
    return response.count if response.count is not None else 0

def delete_metric(metric_id: str):
    """Deletes a metric. Note: This will fail if foreign key constraints 
    exist and entries aren't deleted first."""
    return sb.table("metrics").delete().eq("id", metric_id).execute()

def get_category_by_name(name: str):
    """Finds a category by name for the current user."""
    res = sb.table("categories").select("*").eq("name", name.lower()).execute()
    return res.data[0] if res.data else None

def get_metric_by_name(name: str):
    """Finds a metric by name for the current user."""
    res = sb.table("metrics").select("*").eq("name", name.lower()).execute()
    return res.data[0] if res.data else None

def get_flat_export_data():
    """
    Fetches a flattened dataset for the current user.
    """
    # Uses the simplified model where unit data is inside metrics
    query = sb.table("entries").select(
        "recorded_at, value, metrics(name, unit_name, categories(name))"
    ).execute()
    
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
    """
    Deletes all entries, metrics, and categories for the user.
    Order matters due to foreign key constraints.
    """
    # 1. Delete Entries
    sb.table("entries").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 2. Delete Metrics
    sb.table("metrics").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    # 3. Delete Categories
    sb.table("categories").delete().neq("id", "00000000-0000-0000-0000-000000000000").execute()
    
def save_backup_timestamp():
    """Saves the current time to a local config file."""
    data = {"last_backup": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
    with open("config.json", "w") as f:
        json.dump(data, f)

def get_last_backup_timestamp():
    """Retrieves the last backup time."""
    if os.path.exists("config.json"):
        with open("config.json", "r") as f:
            return json.load(f).get("last_backup", "Never")
    return "Never" 