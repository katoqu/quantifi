import streamlit as st
from supabase import create_client

SUPABASE_URL = st.secrets["connections"]["supabase"]["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["connections"]["supabase"]["SUPABASE_KEY"]

sb = create_client(SUPABASE_URL, SUPABASE_KEY)

def fetch(table: str):
    res = sb.table(table).select("*").execute()
    return res.data or []

def insert(table: str, payload: dict):
    return sb.table(table).insert(payload).execute()
