# capture.py
import streamlit as st
import models
import utils
import datetime as dt
import time
from ui import visualize

def show_tracker_suite(selected_metric, unit_meta):

    # 1. Collect data for this specific metric
    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)
    
    # 2. Show capture form
    show_capture(selected_metric, unit_meta)
    
    st.divider()
    
    # 3. Show visualization
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name)
    else:
        st.info("No data entries found for this metric yet. Use the form above to add your first entry.")

def show_capture(selected_metric, unit_meta):
    # ... (Keep your existing show_capture logic here) ...
    # Ensure it still handles the 'last_val' proposal and state clearing
    st.header("Capture Data")
    
    mid = selected_metric.get("id")
    selected_unit = unit_meta.get(selected_metric.get("unit_id"))
    utype = selected_unit.get("unit_type", "float") if selected_unit else "float"
    
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
            if utype == "integer_range":
                rs, re = int(selected_unit.get("range_start", 0)), int(selected_unit.get("range_end", 100))
                allowed_values = list(range(rs, re + 1))
                start_idx = allowed_values.index(int(proposal_val)) if proposal_val in allowed_values else 0
                val = st.selectbox("Value", options=allowed_values, index=start_idx)
            elif utype == "integer":
                val = st.number_input("Value", step=1, format="%d", value=int(proposal_val or 0))
            else:
                val = st.number_input("Value", format="%.1f", step=1.0, value=float(proposal_val or 0.0))

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

            #Clear the global cache so other pages see the new record
            st.cache_data.clear()

            st.session_state[last_val_key] = val
            state_key = f"data_{mid}"
            if state_key in st.session_state:
                del st.session_state[state_key] # Invalidates edit-page cache
            
            st.toast(f"Saved: {val}", icon="✅")
            time.sleep(0.8)
            st.rerun()