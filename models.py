from supabase_config import sb
import streamlit as st  # <-- ADD THIS LINE

@st.cache_data(ttl=60) # Only fetch from DB once every minute
def get_categories():
    response = sb.table("categories").select("*").execute()
    return response.data

@st.cache_data(ttl=60)
def get_units():
    response = sb.table("units").select("*").execute()
    return response.data

@st.cache_data(ttl=60)
def get_metrics():
    response = sb.table("metrics").select("*").execute()
    if not response.data:
        # We clear the specific cache for this function so the 
        # "No metrics" message doesn't get stuck.
        get_metrics.clear()
    return response.data

def get_entries(metric_id=None):
    query = sb.table("entries").select("*")
    if metric_id:
        # It is more efficient to filter in the database than in Python
        query = query.eq("metric_id", metric_id)
    response = query.execute()
    return response.data

def create_category(name: str):
    return sb.table("categories").insert({"name": name}).execute()

def create_unit(payload: dict):
    return sb.table("units").insert(payload).execute()

def create_metric(payload: dict):
    return sb.table("metrics").insert(payload).execute()

def create_entry(payload: dict):
    return sb.table("entries").insert(payload).execute()

def update_entry(entry_id, payload: dict):
    return sb.table("entries").update(payload).eq("id", entry_id).execute()

def delete_entry(entry_id):
    return sb.table("entries").delete().eq("id", entry_id).execute()
