import streamlit as st
import models
import utils
import datetime as dt
import time
from ui import visualize

def show_tracker_suite(selected_metric):
    """Refactored: Uses metric object directly for units and metadata."""
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet. Add your first enrty below.")    

    show_capture(selected_metric)
    st.divider()
    
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name)

def show_capture(selected_metric):
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # FIX: Ensure smart_default is never None
    last_entry = models.get_latest_entry_only(mid)
    # If no last entry, use range_start; if range_start is missing, use 0.0
    fallback = selected_metric.get("range_start", 0.0)
    smart_default = last_entry['value'] if last_entry else float(fallback if fallback is not None else 0.0)

    with st.container(border=True):
        st.markdown(f"**Recording:** {selected_metric['name'].title()}")

        use_time = st.checkbox(
            "🕒 Include specific time?", 
            value=st.session_state["use_time_sticky"], 
            key="use_time_toggle",
            on_change=lambda: st.session_state.update(
                {"use_time_sticky": st.session_state["use_time_toggle"]}
            )
        )
        
        with st.form("capture_entry_submit", border=False):
            # --- SINGLE COLUMN LAYOUT ---
            # Stacking inputs vertically for better mobile tap targets
            date_input = st.date_input("📅 Date", value=dt.date.today())
            
            time_input = dt.time(12, 0)
            if use_time:
                time_input = st.time_input("⏰ Time", value=dt.datetime.now().time())
            
            # Value Input
            if utype == "integer_range":
                rs = int(selected_metric.get("range_start", 0))
                re = int(selected_metric.get("range_end", 10))
                options = list(range(rs, re + 1))
                default_index = options.index(int(smart_default)) if int(smart_default) in options else 0
                val = st.selectbox(f"Value ({unit_name})", options=options, index=default_index)
            elif utype == "integer":
                val = st.number_input(f"Value ({unit_name})", value=int(smart_default), step=1, format="%d")
            else:
                val = st.number_input(f"Value ({unit_name})", value=float(smart_default), format="%.1f", step=1.0)

            submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
            
            if submitted:
                final_dt = dt.datetime.combine(date_input, time_input)
                models.create_entry({
                    "metric_id": mid, 
                    "value": val, 
                    "recorded_at": final_dt.isoformat()
                })
                # Refresh cache to show new entry in Overview
                st.cache_data.clear() 
                utils.finalize_action(f"Saved: {val} {unit_name}")