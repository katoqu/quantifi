import streamlit as st
import models
import utils
import datetime as dt
from ui import visualize

@st.fragment
def show_tracker_suite(selected_metric):

    # 1. Capture Form
    show_capture(selected_metric)
    
    st.divider()

    # 2. Local Data Fetch (Only within fragment scope)
    dfe, m_unit, m_name = utils.collect_data(selected_metric)

    # 3. Inline Visualization Update
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name)
    else:
        st.info("No data recorded for this metric yet. Add your first entry above.")

def show_capture(selected_metric):
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # Fetch smart default once per fragment execution
    last_entry = models.get_latest_entry_only(mid)
    fallback = selected_metric.get("range_start", 0.0)
    smart_default = last_entry['value'] if last_entry else float(fallback if fallback is not None else 0.0)

    with st.container(border=True):
        if selected_metric.get("description"):
            st.caption(selected_metric["description"])

        # Note: st.form is kept to bundle the inputs
        with st.form("capture_entry_submit", border=False):
            date_input = st.date_input("📅 Date", value=dt.date.today())
            
            time_input = st.time_input(
                "⏰ Time", 
                value=dt.datetime.now().time(),
                step=60
            )
            
            # Value Input Logic
            if utype == "integer_range":
                rs = int(selected_metric.get("range_start", 0))
                re = int(selected_metric.get("range_end", 10))
                default_val = int(smart_default)
                if default_val < rs:
                    default_val = rs
                elif default_val > re:
                    default_val = re
                val = st.slider(
                    f"Value ({unit_name})",
                    min_value=rs,
                    max_value=re,
                    value=default_val,
                    step=1,
                )
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
                
                # REPLACEMENT FOR st.rerun():
                # We clear the specific cache and show a toast. 
                # The fragment will naturally re-run its internal code
                # to show the new data in the chart above.
                st.cache_data.clear() 
                st.toast(f"✅ Saved: {val} {unit_name}")

                st.rerun(scope="fragment")
