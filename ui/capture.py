import streamlit as st
import models
import utils

def show_capture(selected_metric, unit_meta):
    st.header("Capture data")

    if not selected_metric:
        st.warning("No metrics defined yet. Create one in 'Define & configure'.")
        return    

    selected_unit = unit_meta.get(selected_metric.get("unit_id"))

    with st.form("capture_entry"):
        utype = selected_unit.get("unit_type", "float") if selected_unit else "float"
        if utype == "integer_range":
            rs = int(selected_unit.get("range_start", 0))
            re = int(selected_unit.get("range_end", 100))
            st.caption(f"Select an integer in range [{rs}, {re}]")
            allowed_values = list(range(rs, re + 1))
            val = st.selectbox("Value", options=allowed_values)
        elif utype == "integer":
            st.caption("Unit expects integer values")
            val = st.number_input("Value", step=1, format="%d")
        else:
            val = st.number_input("Value", format="%.1f")

        date = st.date_input("Recorded date")
        datetz = utils.to_datetz(date)
        submitted = st.form_submit_button("Add entry")
        
        if submitted:
            valid = True
            # ... (keep your validation logic) ...
            
            if valid:
                models.create_entry({
                    "metric_id": selected_metric.get("id"), 
                    "value": val, 
                    "recorded_at": datetz.isoformat()
                })
                
                # --- NEW: Clear the editor state so it reloads fresh data ---
                state_key = f"data_{selected_metric.get('id')}"
                if state_key in st.session_state:
                    del st.session_state[state_key]
                
                st.success("Entry added")
                st.rerun()