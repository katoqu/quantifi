import streamlit as st
import models
import utils
import datetime as dt
import time
from ui import visualize

def show_tracker_suite(selected_metric):
    """Refactored: Uses metric object directly for units and metadata."""
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    
    show_capture(selected_metric)
    st.divider()
    
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name)
    else:
        st.info("No data entries found. Add your first entry above.")

def show_capture(selected_metric):
#    st.header("Capture Data")
    
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # 1. Date/Time selection logic
    use_time = st.toggle("🕒 Include specific time?", value=False, help="Toggle to record the exact time of entry.")
    
    with st.form("capture_entry_submit", border=True):
        col_date, col_val, col_btn = st.columns([1.2, 1, 0.8])
        
        with col_date:
            date_input = st.date_input("📅 Date", value=dt.date.today())
            time_input = dt.time(12, 0) # Default midday
            if use_time:
                time_input = st.time_input("⏰ Time", value=dt.datetime.now().time())
        
        with col_val:
            # Reusing your existing logic for value types
            if utype == "integer_range":
                rs, re = int(selected_metric.get("range_start", 0)), int(selected_metric.get("range_end", 10))
                val = st.selectbox(f"Value ({unit_name})", options=list(range(rs, re + 1)))
            elif utype == "integer":
                val = st.number_input(f"Value ({unit_name})", step=1, format="%d")
            else:
                val = st.number_input(f"Value ({unit_name})", format="%.1f", step=1.0)

        with col_btn:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
        
        if submitted:
            # Combine date and time for the final timestamp
            final_dt = dt.datetime.combine(date_input, time_input)
            
            models.create_entry({
                "metric_id": mid, 
                "value": val, 
                "recorded_at": final_dt.isoformat()
            })

            st.cache_data.clear()
            # Centralized finish logic
            utils.finalize_action(f"Saved: {val} {unit_name}")