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
    Mobile-optimized capture interface with Smart Defaults and 
    streamlined feedback loops.
    """
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # 1. SMART DEFAULT: Persist the 'Use Time' preference across sessions
    if "use_time_sticky" not in st.session_state:
        st.session_state["use_time_sticky"] = False

    # Toggle updates the session state immediately via callback
    use_time = st.toggle(
        "🕒 Include specific time?", 
        value=st.session_state["use_time_sticky"], 
        help="Toggle to record exact time. This preference is saved.",
        key="use_time_toggle",
        on_change=lambda: st.session_state.update(
            {"use_time_sticky": st.session_state["use_time_toggle"]}
        )
    )
    
    with st.form("capture_entry_submit", border=True):
        # Mobile layout: Date and Time stacked or tight-grouped
        col_date, col_val = st.columns([1, 1])
        
        with col_date:
            date_input = st.date_input("📅 Date", value=dt.date.today())
            time_input = dt.time(12, 0) # Default midday
            if use_time:
                # Use current time as the default for real-time logging
                time_input = st.time_input("⏰ Time", value=dt.datetime.now().time())
        
        with col_val:
            # Reusing existing logic for value types
            if utype == "integer_range":
                rs = int(selected_metric.get("range_start", 0))
                re = int(selected_metric.get("range_end", 10))
                # Selectbox is easier to hit on mobile than number_input for small ranges
                val = st.selectbox(f"Value ({unit_name})", options=list(range(rs, re + 1)))
            elif utype == "integer":
                val = st.number_input(f"Value ({unit_name})", step=1, format="%d")
            else:
                val = st.number_input(f"Value ({unit_name})", format="%.1f", step=1.0)

        # Full-width 'primary' button for easy thumb access
        submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
        
        if submitted:
            # Combine date and time for the final timestamp
            final_dt = dt.datetime.combine(date_input, time_input)
            
            # Save to backend
            models.create_entry({
                "metric_id": mid, 
                "value": val, 
                "recorded_at": final_dt.isoformat()
            })

            # 2. OPTIMIZED FEEDBACK: Uses the new centralized helper in utils.py
            # This clears cache, shows a toast, and reruns the app.
            utils.finalize_action(f"Saved: {val} {unit_name}")