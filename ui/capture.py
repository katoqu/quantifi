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
    """
    Mobile-optimized capture interface with Smart Defaults.
    Pre-fills the input with the last recorded value for this metric.
    """
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # --- 1. SMART DEFAULT LOGIC ---
    # Fetch existing entries to find the "Ghost Value"
    entries = models.get_entries(metric_id=mid)
    if entries:
        # Sort by recorded_at to ensure we get the absolute latest
        last_entry = sorted(entries, key=lambda x: x['recorded_at'])[-1]
        smart_default = last_entry['value']
    else:
        # Fallback to range_start or 0.0 if no history exists
        smart_default = float(selected_metric.get("range_start", 0.0))

    # --- 2. PREFERENCE PERSISTENCE ---
    if "use_time_sticky" not in st.session_state:
        st.session_state["use_time_sticky"] = False

    use_time = st.toggle(
        "🕒 Include specific time?", 
        value=st.session_state["use_time_sticky"], 
        key="use_time_toggle",
        on_change=lambda: st.session_state.update(
            {"use_time_sticky": st.session_state["use_time_toggle"]}
        )
    )
    
    with st.form("capture_entry_submit", border=True):
        col_date, col_val = st.columns([1, 1])
        
        with col_date:
            date_input = st.date_input("📅 Date", value=dt.date.today())
            time_input = dt.time(12, 0)
            if use_time:
                time_input = st.time_input("⏰ Time", value=dt.datetime.now().time())
        
        with col_val:
            # --- 3. APPLY SMART DEFAULTS TO INPUTS ---
            if utype == "integer_range":
                rs = int(selected_metric.get("range_start", 0))
                re = int(selected_metric.get("range_end", 10))
                
                # Determine index for selectbox based on smart_default
                options = list(range(rs, re + 1))
                default_index = options.index(int(smart_default)) if int(smart_default) in options else 0
                
                val = st.selectbox(f"Value ({unit_name})", options=options, index=default_index)
                
            elif utype == "integer":
                # Pre-fill number_input with smart_default
                val = st.number_input(f"Value ({unit_name})", value=int(smart_default), step=1, format="%d")
                
            else:
                # Pre-fill float input with smart_default
                val = st.number_input(f"Value ({unit_name})", value=float(smart_default), format="%.1f", step=1.0)

        submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
        
        if submitted:
            final_dt = dt.datetime.combine(date_input, time_input)
            models.create_entry({
                "metric_id": mid, 
                "value": val, 
                "recorded_at": final_dt.isoformat()
            })
            utils.finalize_action(f"Saved: {val} {unit_name}")