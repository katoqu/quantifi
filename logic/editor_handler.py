import streamlit as st
import pandas as pd
import models
import datetime as dt
from datetime import timedelta

def process_save_to_backend(mid, df, state, to_delete, to_update, to_add):
    """Executes database operations and resets relevant state."""
    for _, row in to_delete.iterrows():
        if pd.notna(row.get("id")):
            models.delete_entry(row["id"])

    for _, row in to_update.iterrows():
        rid = row.get("id")
        if pd.notna(rid):
            payload = {
                "value": float(row["value"]),
                "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
            }
            models.update_entry(rid, payload)

    for row in to_add:
        if row.get("value") is not None:
            models.create_entry({
                "value": float(row["value"]),
                "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                "metric_id": mid
            })
    
    st.cache_data.clear()
    state_key = f"data_{mid}"
    if state_key in st.session_state:
        del st.session_state[state_key]

import streamlit as st
import pandas as pd
import models
import datetime as dt
from datetime import timedelta

def get_date_bounds(dfe, mid):
    """Calculates boundaries and ensures state keys are valid tuples for unpacking."""
    dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'])
    abs_min = dfe['recorded_at'].min().date()
    abs_max = dfe['recorded_at'].max().date()

    date_picker_key = f"date_range_{mid}"
    prev_date_key = f"prev_date_{mid}"
    default_range = (abs_min, abs_max)

    # 1. Initialize backup key if missing
    if prev_date_key not in st.session_state:
        st.session_state[prev_date_key] = default_range
    
    # 2. DEFENSIVE CHECK: Ensure prev_date_key is actually a tuple of 2
    # If it became a single date (the cause of your ValueError), reset it.
    stored_val = st.session_state[prev_date_key]
    if not isinstance(stored_val, (tuple, list)) or len(stored_val) != 2:
        st.session_state[prev_date_key] = default_range
        
    # Now it is guaranteed safe to unpack
    stored_min, stored_max = st.session_state[prev_date_key]

    # 3. Handle data expansion
    if abs_min < stored_min or abs_max > stored_max:
        new_range = (min(abs_min, stored_min), max(abs_max, stored_max))
        st.session_state[prev_date_key] = new_range
        # Only overwrite the active picker if the user isn't mid-selection
        if date_picker_key not in st.session_state:
            st.session_state[date_picker_key] = new_range

    # 4. Initialize the widget key if it's missing
    if date_picker_key not in st.session_state:
        st.session_state[date_picker_key] = st.session_state[prev_date_key]
                
    return abs_min, abs_max

def has_unsaved_changes(state_key):
    """Checks for pending edits in the session state."""
    if state_key in st.session_state:
        return (st.session_state[state_key]["Change Log"] != "").any()
    return False