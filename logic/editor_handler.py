import streamlit as st
import pandas as pd
import models
import utils
import datetime as dt

def get_date_bounds(dfe, mid):
    """Calculates boundaries and ensures baseline state exists."""
    dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], format='ISO8601', utc=True)
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
        st.session_state[prev_key] = (curr_start, curr_end)
    return False

def has_unsaved_changes(state_key):
    """Checks for non-empty change log strings."""
    if state_key in st.session_state:
        log = st.session_state[state_key].get("Change Log", pd.Series(dtype=str)).fillna('')
        return (log != "").any()
    return False

def reset_editor_state(state_key, mid=None):
    """Clears draft and baseline."""
    if state_key in st.session_state:
        del st.session_state[state_key]
    
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
    """
    Separates table cues (emojis) from detailed audit logs.
    """
    state = st.session_state[editor_key]
    df = st.session_state[state_key]
    
    for idx, changes in state.get("edited_rows", {}).items():
        actual_idx = view_df_indices[idx]
        for col, val in changes.items():
            # Apply the update
            df.at[actual_idx, col] = val
            
            # 1. TABLE CUE: Short emoji for narrow mobile screens
            if col == "Select":
                df.at[actual_idx, "Change Log"] = "🔴" if val else ""
            elif "🔴" not in str(df.at[actual_idx, "Change Log"]):
                # Mark as edited without long text
                df.at[actual_idx, "Change Log"] = "🟡"

def get_change_summary(state_key, editor_key):
    """
    Aggregates change types using the new single-emoji markers.
    """
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    return {
        # Identify rows by their specific emoji markers
        "del": len(df[df["Change Log"] == "🔴"]),
        "upd": len(df[df["Change Log"] == "🟡"]),
        "add": len(state.get("added_rows", []))
    }

def execute_save(mid, state_key, editor_key):
    """
    Commits all deletions, updates, and new rows to Supabase.
    Updated to recognize single-emoji status markers.
    """
    df = st.session_state[state_key]
    state = st.session_state[editor_key]

    # Fetch metric metadata for range validation
    res = models._safe_execute(models.sb.table("metrics").select("*").eq("id", mid))
    metric = res.data[0] if res and res.data else {}
    is_range = metric.get("unit_type") == "integer_range"
    r_min = metric.get("range_start", 0)
    r_max = metric.get("range_end", 10)
    
    # 1. PROCESS DELETIONS
    # Logic now looks specifically for the red circle emoji
    for _, row in df[df["Change Log"] == "🔴"].iterrows():
        if pd.notna(row.get("id")):
            models.delete_entry(row["id"])

    # 2. PROCESS UPDATES
    # Logic now looks specifically for the yellow circle emoji
    for _, row in df[df["Change Log"] == "🟡"].iterrows():
        rid = row.get("id")
        val = float(row["value"])
        
        # Range Validation
        if is_range and not (r_min <= val <= r_max):
            st.error(f"Save failed: {val} is outside valid range ({r_min}-{r_max})")
            return

        if pd.notna(rid):
            models.update_entry(rid, {
                "value": val,
                "recorded_at": pd.to_datetime(row["recorded_at"], format='ISO8601', utc=True).isoformat()
            })

    # 3. PROCESS ADDITIONS (Unchanged, as they come from 'added_rows' state)
    for row in state.get("added_rows", []):
        if row.get("value") is not None:
            val = float(row["value"])
            if is_range and not (r_min <= val <= r_max):
                st.error(f"Save failed: New value {val} is outside range ({r_min}-{r_max})")
                return

            models.create_entry({
                "value": val,
                "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now()), format='ISO8601', utc=True).isoformat(),
                "metric_id": mid
            })

    # Reset state and provide feedback

    reset_editor_state(state_key, mid)
    utils.finalize_action("Changes pushed to database")