from supabase_config import sb
import streamlit as st

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