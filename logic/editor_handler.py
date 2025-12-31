import streamlit as st
import pandas as pd
import models
import datetime as dt

def get_date_bounds(dfe, mid):
    """Calculates boundaries and ensures state keys are valid."""
    dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'])
    abs_min = dfe['recorded_at'].min().date()
    abs_max = dfe['recorded_at'].max().date()

    prev_date_key = f"prev_date_{mid}"
    if prev_date_key not in st.session_state:
        st.session_state[prev_date_key] = (abs_min, abs_max)
                
    return abs_min, abs_max

def is_date_conflict(mid, state_key):
    """Checks if date range changed while unsaved edits exist."""
    date_key = f"date_range_{mid}"
    prev_key = f"prev_date_{mid}"
    
    if date_key not in st.session_state or prev_key not in st.session_state:
        return False

    curr = st.session_state[date_key]
    prev = st.session_state[prev_key]
    
    if isinstance(curr, (tuple, list)) and len(curr) == 2:
        if curr != prev:
            if has_unsaved_changes(state_key):
                return True
            # Auto-sync tracker if no changes exist, allowing the filter update
            st.session_state[prev_key] = curr
    return False

def has_unsaved_changes(state_key):
    """Checks for non-empty change log strings, handling NaNs safely."""
    if state_key in st.session_state:
        log = st.session_state[state_key].get("Change Log", pd.Series(dtype=str)).fillna('')
        return (log != "").any()
    return False

def reset_editor_state(state_key, mid=None):
    """Clears draft and syncs date trackers to accept current picker value."""
    if state_key in st.session_state:
        del st.session_state[state_key]
    if mid:
        st.session_state[f"prev_date_{mid}"] = st.session_state.get(f"date_range_{mid}")

def sync_editor_changes(state_key, editor_key, view_df_indices):
    """Maps edits from the visible view back to the master draft."""
    state = st.session_state[editor_key]
    df = st.session_state[state_key]
    
    for idx, changes in state.get("edited_rows", {}).items():
        # Map table row index to the actual DataFrame index
        actual_idx = view_df_indices[idx]
        for col, val in changes.items():
            df.at[actual_idx, col] = val
            if col == "Select":
                df.at[actual_idx, "Change Log"] = "🗑️ DELETED" if val else ""
            elif "🗑️" not in str(df.at[actual_idx, "Change Log"]):
                df.at[actual_idx, "Change Log"] = "📝 Edited"

def get_change_summary(state_key, editor_key):
    """Aggregates counts of deletions, updates, and additions."""
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    return {
        "del": len(df[df["Change Log"] == "🗑️ DELETED"]),
        "upd": len(df[df["Change Log"].str.contains("📝", na=False)]),
        "add": len(state.get("added_rows", []))
    }

def execute_save(mid, state_key, editor_key):
    """Handles the final database push for all pending changes in the master state."""
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    
    to_delete = df[df["Change Log"] == "🗑️ DELETED"]
    to_update = df[df["Change Log"].str.contains("📝", na=False)]
    to_add = state.get("added_rows", [])

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
    reset_editor_state(state_key, mid)