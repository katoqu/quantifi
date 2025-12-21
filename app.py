import streamlit as st
import pandas as pd
import plotly.express as px
from supabase import create_client

SUPABASE_URL = st.secrets["SUPABASE_URL"]
SUPABASE_KEY = st.secrets["SUPABASE_KEY"]
sb = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("Simple Metric Tracker")

# Add metric
with st.expander("Add metric"):
    mn = st.text_input("Name")
    mc = st.text_input("Category")
    mu = st.text_input("Unit")
    if st.button("Create metric"):
        sb.table("metrics").insert({"name": mn, "category": mc, "unit": mu}).execute()
        st.success("Metric created")

# Select metric
metrics = sb.table("metrics").select("*").execute().data
dfm = pd.DataFrame(metrics)
metric = st.selectbox("Metric", dfm["id"].tolist(), format_func=lambda i: dfm.loc[dfm['id']==i,'name'].values[0] if not dfm.empty else "")

# Add entry
with st.form("entry"):
    val = st.number_input("Value", format="%.3f")
    date = st.date_input("Recorded date")
    submitted = st.form_submit_button("Add entry")
    if submitted:
        sb.table("entries").insert({"metric_id": metric, "value": val, "recorded_at": date}).execute()
        st.success("Entry added")

# Show entries and plot
entries = sb.table("entries").select("*").eq("metric_id", metric).order("recorded_at", {"ascending": True}).execute().data
dfe = pd.DataFrame(entries)
if not dfe.empty:
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    st.dataframe(dfe[["recorded_at","value"]])
    fig = px.line(dfe, x="recorded_at", y="value", title="Time course")
    st.plotly_chart(fig)
else:
    st.info("No entries yet for this metric.")