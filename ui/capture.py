import streamlit as st
import models
import utils

def show_capture(selected_metric, unit_meta):
    st.header("Capture data")

    if not selected_metric:
        st.warning("No metrics defined yet. Create one in 'Define & configure'.")
        return    

    mid = selected_metric.get("id")
    selected_unit = unit_meta.get(selected_metric.get("unit_id"))
    utype = selected_unit.get("unit_type", "float") if selected_unit else "float"
    
    # 1. Proposal Logic: Check session state first, then database
    last_val_key = f"last_val_{mid}"
    proposal_val = st.session_state.get(last_val_key)

    if proposal_val is None:
        # Fetch the very last entry for this metric from the database
        recent_entries = models.get_entries(metric_id=mid)
        if recent_entries:
            # Entries are sorted by recorded_at in the DB typically, 
            # but we'll sort to be safe and take the most recent
            recent_entries.sort(key=lambda x: x["recorded_at"], reverse=True)
            proposal_val = recent_entries[0].get("value")
            # Store it so we don't query the DB on every button click
            st.session_state[last_val_key] = proposal_val

    # 2. Reactive Inputs with Step Size = 1.0
    if utype == "integer_range":
        rs = int(selected_unit.get("range_start", 0))
        re = int(selected_unit.get("range_end", 100))
        st.caption(f"Select an integer in range [{rs}, {re}]")
        allowed_values = list(range(rs, re + 1))
        
        start_idx = 0
        if proposal_val is not None and int(proposal_val) in allowed_values:
            start_idx = allowed_values.index(int(proposal_val))
            
        val = st.selectbox("Value", options=allowed_values, index=start_idx)
        
    elif utype == "integer":
        st.caption("Unit expects integer values")
        val = st.number_input("Value", step=1, format="%d", value=int(proposal_val) if proposal_val is not None else 0)
        
    else:
        # FEATURE: Step size set to 1.0 for easier whole-number adjustments
        val = st.number_input(
            "Value", 
            format="%.1f", 
            step=1.0, 
            value=float(proposal_val) if proposal_val is not None else 0.0
        )

    # 3. Submission Logic
    with st.form("capture_entry_submit"):
        date = st.date_input("Recorded date")
        submitted = st.form_submit_button("Add entry", use_container_width=True)
        
        if submitted:
            datetz = utils.to_datetz(date)
            models.create_entry({
                "metric_id": mid, 
                "value": val, 
                "recorded_at": datetz.isoformat()
            })
            
            # Update the proposal immediately
            st.session_state[last_val_key] = val
            
            # Clear editor state to show the new entry in the table
            state_key = f"data_{mid}"
            if state_key in st.session_state:
                del st.session_state[state_key]
            
            st.success(f"Entry added: {val}")
            st.rerun()