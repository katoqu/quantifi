# capture.py
import streamlit as st
import models
import utils
import datetime as dt
import time
from ui import visualize

def show_tracker_suite(selected_metric):
    """
    Refactored: No longer requires unit_meta. 
    Information is accessed directly from selected_metric.
    """
    # 1. Collect data using the metric's internal unit info
    # We pass None for unit_meta as collect_data should be updated to handle this
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    
    # 2. Show capture form
    show_capture(selected_metric)
    
    st.divider()
    
    # 3. Show visualization
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name)
    else:
        st.info("No data entries found for this metric yet. Use the form above to add your first entry.")

def show_capture(selected_metric):
    st.header("Capture Data")
    
    mid = selected_metric.get("id")
    # Access unit info directly from the metric object
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    last_val_key = f"last_val_{mid}"
    proposal_val = st.session_state.get(last_val_key)

    if proposal_val is None:
        recent_entries = models.get_entries(metric_id=mid)
        if recent_entries:
            recent_entries.sort(key=lambda x: x["recorded_at"], reverse=True)
            proposal_val = recent_entries[0].get("value")
            st.session_state[last_val_key] = proposal_val

    with st.form("capture_entry_submit", border=True):
        col_date, col_val, col_btn = st.columns([1.2, 1, 0.8])
        with col_date:
            date = st.date_input("📅 Date", value=dt.date.today())
        with col_val:
            # Logic now uses the metric's direct properties
            if utype == "integer_range":
                rs = int(selected_metric.get("range_start", 0))
                re = int(selected_metric.get("range_end", 100))
                allowed_values = list(range(rs, re + 1))
                start_idx = allowed_values.index(int(proposal_val)) if proposal_val in allowed_values else 0
                val = st.selectbox(f"Value ({unit_name})", options=allowed_values, index=start_idx)
            elif utype == "integer":
                val = st.number_input(f"Value ({unit_name})", step=1, format="%d", value=int(proposal_val or 0))
            else:
                val = st.number_input(f"Value ({unit_name})", format="%.1f", step=1.0, value=float(proposal_val or 0.0))

        with col_btn:
            st.markdown("<div style='padding-top: 28px;'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
        
        if submitted:
            datetz = utils.to_datetz(date)
            models.create_entry({
                "metric_id": mid, 
                "value": val, 
                "recorded_at": datetz.isoformat()
            })

            st.cache_data.clear()
            st.session_state[last_val_key] = val
            state_key = f"data_{mid}"
            if state_key in st.session_state:
                del st.session_state[state_key] 
            
            st.toast(f"Saved: {val} {unit_name}", icon="✅")
            time.sleep(0.8)
            st.rerun()