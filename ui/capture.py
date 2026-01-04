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
    Visual Hack: Wraps a borderless form and a toggle in a single container 
    to make them look like one unified recording suite.
    """
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # --- 1. SMART DEFAULT LOGIC (Stable) ---
    entries = models.get_entries(metric_id=mid)
    if entries:
        last_entry = sorted(entries, key=lambda x: x['recorded_at'])[-1]
        smart_default = last_entry['value']
    else:
        smart_default = float(selected_metric.get("range_start", 0.0))

    if "use_time_sticky" not in st.session_state:
        st.session_state["use_time_sticky"] = False

    # --- 2. THE OUTER "FAKE" BOX ---
    # We use a container with a border to act as the primary visual frame
    with st.container(border=True):
        
        # Identity Row: Small hint of what we are recording
        st.markdown(f"**Recording:** {selected_metric['name'].title()}")

        # --- 3. THE TOGGLE (Outside the form, but inside the border) ---
        use_time = st.checkbox(
            "🕒 Include specific time?", 
            value=st.session_state["use_time_sticky"], 
            key="use_time_toggle",
            on_change=lambda: st.session_state.update(
                {"use_time_sticky": st.session_state["use_time_toggle"]}
            )
        )
        
#        st.markdown("<div style='margin-bottom: -55px;'></div>", unsafe_allow_html=True)

        # --- 4. THE BORDERLESS FORM ---
        # Setting border=False makes the form invisible, 
        # so it blends into the container above.
        with st.form("capture_entry_submit", border=False):
            col_date, col_val = st.columns([1, 1])
            
            with col_date:
                date_input = st.date_input("📅 Date", value=dt.date.today())
                time_input = dt.time(12, 0)
                if use_time:
                    time_input = st.time_input("⏰ Time", value=dt.datetime.now().time())
            
            with col_val:
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
                utils.finalize_action(f"Saved: {val} {unit_name}")