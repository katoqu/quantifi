import streamlit as st
import pandas as pd
import models
import utils
import datetime as dt

def get_pill_range(selection, abs_min, abs_max):
    """Calculates start/end dates based on pill selection."""
    today = dt.date.today()
    # Support both title case and lowercase variations from different UI components
    sel = selection.lower() if selection else ""
    
    if "week" in sel:
        return today - dt.timedelta(days=7), today
    elif "month" in sel:
        return today - dt.timedelta(days=30), today
    elif "year" in sel:
        return today - dt.timedelta(days=365), today
    elif "all time" in sel:
        return abs_min, abs_max
    return None, None 

def get_date_bounds(dfe, mid):
    """Calculates boundaries and ensures baseline state exists."""
    # Ensure datetime conversion is robust
    dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], utc=True)
    abs_min = dfe['recorded_at'].min().date()
    abs_max = dfe['recorded_at'].max().date()
    
    prev_date_key = f"prev_date_{mid}"
    if prev_date_key not in st.session_state:
        st.session_state[prev_date_key] = (abs_min, abs_max)
    return abs_min, abs_max

def is_date_conflict(mid, state_key):
    """Checks for UI filter changes vs unsaved draft edits."""
    pill_key = f"pill_{mid}"
    start_key = f"start_date_{mid}"
    end_key = f"end_date_{mid}"
    prev_key = f"prev_date_{mid}"
    prev_pill_key = f"prev_pill_{mid}"
    
    if start_key not in st.session_state or end_key not in st.session_state:
        return False

    curr_start, curr_end = st.session_state[start_key], st.session_state[end_key]
    curr_pill = st.session_state.get(pill_key)
    prev_start, prev_end = st.session_state.get(prev_key, (None, None))
    prev_pill = st.session_state.get(prev_pill_key)
    
    # Check if filters have moved
    if curr_start != prev_start or curr_end != prev_end or curr_pill != prev_pill:
        if has_unsaved_changes(state_key):
            return True
        # If no changes, update the baseline to the current filter state
        st.session_state[prev_key] = (curr_start, curr_end)
        st.session_state[prev_pill_key] = curr_pill
    return False

def has_unsaved_changes(state_key):
    """Checks for non-empty change log strings in the draft."""
    if state_key in st.session_state:
        log = st.session_state[state_key].get("Change Log", pd.Series(dtype=str)).fillna('')
        return (log != "").any()
    return False

def reset_editor_state(state_key, mid=None):
    """
    Clears draft and baseline without deleting keys to maintain state stability.
    Deleting keys often causes full-page reruns in fragments.
    """
    if state_key in st.session_state:
        # Re-initialize as an empty dataframe with the correct columns
        cols = st.session_state[state_key].columns
        st.session_state[state_key] = pd.DataFrame(columns=cols)
    
    saved_key = f"saved_data_{mid}"
    if saved_key in st.session_state:
        st.session_state[saved_key] = pd.DataFrame()

    if mid:
        # Synchronize baselines so the conflict warning doesn't immediately re-trigger
        st.session_state[f"prev_date_{mid}"] = (
            st.session_state.get(f"start_date_{mid}"),
            st.session_state.get(f"end_date_{mid}")
        )
        st.session_state[f"prev_pill_{mid}"] = st.session_state.get(f"pill_{mid}")

def revert_date_range(mid):
    """Snaps UI pickers back to the last safe baseline saved in session state."""
    prev_key = f"prev_date_{mid}"
    prev_pill_key = f"prev_pill_{mid}"
    if prev_key in st.session_state:
        st.session_state[f"start_date_{mid}"], st.session_state[f"end_date_{mid}"] = st.session_state[prev_key]
    if prev_pill_key in st.session_state:
        st.session_state[f"pill_{mid}"] = st.session_state[prev_pill_key]

def sync_editor_changes(state_key, editor_key, view_df_indices):
    """Marks rows in the master draft based on data_editor interaction."""
    if editor_key not in st.session_state:
        return
        
    state = st.session_state[editor_key]
    df = st.session_state[state_key]
    
    for idx, changes in state.get("edited_rows", {}).items():
        actual_idx = view_df_indices[idx]
        for col, val in changes.items():
            df.at[actual_idx, col] = val
            # Update visual status markers
            if col == "Select":
                df.at[actual_idx, "Change Log"] = "🔴" if val else ""
            elif "🔴" not in str(df.at[actual_idx, "Change Log"]):
                df.at[actual_idx, "Change Log"] = "🟡"

def get_change_summary(state_key, editor_key):
    """Counts pending updates for the confirmation dialog."""
    df = st.session_state[state_key]
    state = st.session_state.get(editor_key, {})
    return {
        "del": len(df[df["Change Log"] == "🔴"]),
        "upd": len(df[df["Change Log"] == "🟡"]),
        "add": len(state.get("added_rows", []))
    }

def execute_save(mid, state_key, editor_key):
    """Commits all pending edits to the database and refreshes state."""
    df = st.session_state[state_key]
    state = st.session_state.get(editor_key, {})
    
    # 1. Process Deletions
    for _, row in df[df["Change Log"] == "🔴"].iterrows():
        if pd.notna(row.get("id")): 
            models.delete_entry(row["id"])
            
    # 2. Process Updates
    for _, row in df[df["Change Log"] == "🟡"].iterrows():
        if pd.notna(row.get("id")):
            models.update_entry(row["id"], {
                "value": float(row["value"]), 
                "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
            })
            
    # 3. Process New Rows
    for row in state.get("added_rows", []):
        if row.get("value") is not None:
            models.create_entry({
                "value": float(row["value"]), 
                "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(), 
                "metric_id": mid
            })
            
    # Clean up and trigger a full rerun to ensure visualizers fetch fresh DB data
    reset_editor_state(state_key, mid)
    utils.finalize_action("Changes Saved Successfully!")
    st.rerun()