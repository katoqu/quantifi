import streamlit as st
import pandas as pd
import models
import datetime as dt

def get_date_bounds(dfe, mid):
    """Calculates boundaries and ensures baseline state exists."""
    dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'])
    abs_min = dfe['recorded_at'].min().date()
    abs_max = dfe['recorded_at'].max().date()

    prev_date_key = f"prev_date_{mid}"
    if prev_date_key not in st.session_state:
        st.session_state[prev_date_key] = (abs_min, abs_max)
                
    return abs_min, abs_max

def is_date_conflict(mid, state_key):
    """Checks for UI date changes vs unsaved draft edits."""
    start_key = f"start_date_{mid}"
    end_key = f"end_date_{mid}"
    prev_key = f"prev_date_{mid}"
    
    if start_key not in st.session_state or end_key not in st.session_state:
        return False

    curr_start = st.session_state[start_key]
    curr_end = st.session_state[end_key]
    prev_start, prev_end = st.session_state.get(prev_key, (None, None))
    
    if curr_start != prev_start or curr_end != prev_end:
        if has_unsaved_changes(state_key):
            return True
        # Sync baseline if no edits exist to allow UI refresh
        st.session_state[prev_key] = (curr_start, curr_end)
    return False

def has_unsaved_changes(state_key):
    """Checks for non-empty change log strings."""
    if state_key in st.session_state:
        log = st.session_state[state_key].get("Change Log", pd.Series(dtype=str)).fillna('')
        return (log != "").any()
    return False

def reset_editor_state(state_key, mid=None):
    """Clears draft and baseline. The graph will revert to DB state on next rerun."""
    if state_key in st.session_state:
        del st.session_state[state_key]
    
    # Clear the saved_data cache so it re-initializes from the fresh DB pull
    saved_key = f"saved_data_{mid}"
    if saved_key in st.session_state:
        del st.session_state[saved_key]
        
    if mid:
        st.session_state[f"prev_date_{mid}"] = (
            st.session_state.get(f"start_date_{mid}"),
            st.session_state.get(f"end_date_{mid}")
        )

def revert_date_range(mid):
    """Snaps UI pickers back to the last safe baseline."""
    prev_key = f"prev_date_{mid}"
    if prev_key in st.session_state:
        prev_start, prev_end = st.session_state[prev_key]
        st.session_state[f"start_date_{mid}"] = prev_start
        st.session_state[f"end_date_{mid}"] = prev_end

def sync_editor_changes(state_key, editor_key, view_df_indices):
    """Maps visible table edits back to the master session state dataframe."""
    state = st.session_state[editor_key]
    df = st.session_state[state_key]
    
    for idx, changes in state.get("edited_rows", {}).items():
        actual_idx = view_df_indices[idx]
        for col, val in changes.items():
            df.at[actual_idx, col] = val
            if col == "Select":
                df.at[actual_idx, "Change Log"] = "🗑️ DELETED" if val else ""
            elif "🗑️" not in str(df.at[actual_idx, "Change Log"]):
                df.at[actual_idx, "Change Log"] = "📝 Edited"

def get_change_summary(state_key, editor_key):
    """Aggregates change types for the confirmation dialog."""
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    return {
        "del": len(df[df["Change Log"] == "🗑️ DELETED"]),
        "upd": len(df[df["Change Log"].str.contains("📝", na=False)]),
        "add": len(state.get("added_rows", []))
    }


def execute_save(mid, state_key, editor_key):
    """Commits all deletions, updates, and new rows to Supabase."""
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    
    # Process Deletes
    for _, row in df[df["Change Log"] == "🗑️ DELETED"].iterrows():
        if pd.notna(row.get("id")):
            models.delete_entry(row["id"])

    # Process Updates
    for _, row in df[df["Change Log"].str.contains("📝", na=False)].iterrows():
        rid = row.get("id")
        if pd.notna(rid):
            models.update_entry(rid, {
                "value": float(row["value"]),
                "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
            })

    # Process Adds
    for row in state.get("added_rows", []):
        if row.get("value") is not None:
            models.create_entry({
                "value": float(row["value"]),
                "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                "metric_id": mid
            })
    
    st.cache_data.clear()
    reset_editor_state(state_key, mid)