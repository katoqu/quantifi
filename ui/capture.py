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
        # --- DYNAMIC INPUT LOGIC START ---
        if utype == "integer_range":
            rs = int(selected_unit.get("range_start", 0))
            re = int(selected_unit.get("range_end", 100))
            st.caption(f"Select an integer in range [{rs}, {re}]")
            
            # Create a list of allowed integers for the dropdown
            # selectbox provides native type-ahead search
            allowed_values = list(range(rs, re + 1))
            val = st.selectbox("Value", options=allowed_values)
            
        elif utype == "integer":
            st.caption("Unit expects integer values")
            val = st.number_input("Value", step=1, format="%d")
        else:
            val = st.number_input("Value", format="%.1f")
        # --- DYNAMIC INPUT LOGIC END ---

        date = st.date_input("Recorded date")
        datetz = utils.to_datetz(date)
        submitted = st.form_submit_button("Add entry")
        
        if submitted:
            valid = True
            if selected_unit:
                if utype == "integer":
                    if not float(val).is_integer():
                        st.error("Value must be an integer for this unit")
                        valid = False
                    else:
                        val = int(val)
                elif utype == "integer_range":
                    if not float(val).is_integer():
                        st.error("Value must be an integer for this unit")
                        valid = False
                    else:
                        ival = int(val)
                        rs = selected_unit.get("range_start")
                        re = selected_unit.get("range_end")
                        try:
                            if rs is not None and ival < int(rs):
                                st.error(f"Value must be >= {rs}")
                                valid = False
                            if re is not None and ival > int(re):
                                st.error(f"Value must be <= {re}")
                                valid = False
                        except ValueError:
                            st.error("Invalid stored unit range configuration")
                            valid = False
                        if valid:
                            val = ival

            if valid:
                models.create_entry({"metric_id": selected_metric.get("id"), "value": val, "recorded_at": datetz.isoformat()})
                st.success("Entry added")
                st.rerun() 