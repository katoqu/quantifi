import json
import streamlit as st
import pandas as pd
import models
import utils
import cache_control
import datetime as dt

def get_pill_range(selection, abs_min, abs_max):
    """Calculates start/end dates based on pill selection."""
    # Support both title case and lowercase variations from different UI components
    sel = selection.lower() if selection else ""
    end_date = abs_max if abs_max else dt.date.today()
    
    if "week" in sel:
        return end_date - dt.timedelta(days=7), end_date
    elif "month" in sel:
        return end_date - dt.timedelta(days=31), end_date
    elif "year" in sel:
        return end_date - dt.timedelta(days=365), end_date
    elif sel in {"all", "all time"} or "all time" in sel:
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

def reset_editor_state(state_key, mid=None):
    """
    Clears draft and baseline without deleting keys to maintain state stability.
    Ensures that columns remain present to avoid KeyErrors in visualizations.
    """
    # Define the exact columns your application logic expects
    standard_cols = ["id", "recorded_at", "value", "Change Log", "Select"]

    if state_key in st.session_state:
        st.session_state[state_key] = pd.DataFrame(columns=standard_cols)

    saved_key = f"saved_data_{mid}"
    if saved_key in st.session_state:
        st.session_state[saved_key] = pd.DataFrame(columns=standard_cols)

    if mid:
        # Synchronize baselines so the conflict warning doesn't immediately re-trigger
        st.session_state[f"prev_date_{mid}"] = (
            st.session_state.get(f"start_date_{mid}"),
            st.session_state.get(f"end_date_{mid}")
        )
        st.session_state[f"prev_pill_{mid}"] = st.session_state.get(f"pill_{mid}")

def prepare_entry_editor_frame(frame, metric_kind=None):
    """Adds editor-friendly columns for structured strength-session rows."""
    if frame is None:
        return pd.DataFrame(columns=["id", "recorded_at", "value", "Change Log", "Select"])

    view_df = frame.copy()
    if metric_kind == "strength_session" or "load_kg" in view_df.columns or "sets" in view_df.columns:
        if "load_kg" not in view_df.columns:
            view_df["load_kg"] = pd.NA
        if "reps_per_set" not in view_df.columns:
            view_df["reps_per_set"] = pd.NA
        if "set_count" not in view_df.columns:
            view_df["set_count"] = pd.NA

        for idx, row in view_df.iterrows():
            load_value = row.get("load_kg")
            if pd.isna(load_value) or load_value is None:
                load_value = row.get("value")
            if pd.notna(load_value):
                view_df.at[idx, "load_kg"] = load_value

            sets = row.get("sets") or []
            if isinstance(sets, list) and sets:
                reps_values = [int(s.get("reps", 0)) for s in sets if isinstance(s, dict)]
                if reps_values:
                    view_df.at[idx, "reps_per_set"] = reps_values[0]
                view_df.at[idx, "set_count"] = len(sets)
            if pd.isna(view_df.at[idx, "reps_per_set"]) or view_df.at[idx, "reps_per_set"] is None:
                view_df.at[idx, "reps_per_set"] = 1
            if pd.isna(view_df.at[idx, "set_count"]) or view_df.at[idx, "set_count"] is None:
                view_df.at[idx, "set_count"] = 1

        view_df["load_kg"] = pd.to_numeric(view_df["load_kg"], errors="coerce")
        view_df["reps_per_set"] = pd.to_numeric(view_df["reps_per_set"], errors="coerce").fillna(1).astype(int)
        view_df["set_count"] = pd.to_numeric(view_df["set_count"], errors="coerce").fillna(1).astype(int)

    return view_df


def _coerce_strength_sets(row):
    """Extract structured set data from a row when present."""
    raw_sets = row.get("sets")
    if isinstance(raw_sets, list):
        return raw_sets
    if isinstance(raw_sets, str):
        try:
            parsed = json.loads(raw_sets)
        except Exception:
            return []
        if isinstance(parsed, list):
            return parsed
    return []


def _coerce_strength_payload(row):
    """Build a structured strength-session payload from editable table values."""
    payload = {}
    raw_load = row.get("load_kg")
    if raw_load is None or (isinstance(raw_load, float) and pd.isna(raw_load)) or (isinstance(raw_load, str) and raw_load.strip() == ""):
        payload["load_kg"] = None
    else:
        payload["load_kg"] = float(raw_load)

    if "reps_per_set" in row or "set_count" in row:
        reps_per_set = row.get("reps_per_set")
        set_count = row.get("set_count")
        if payload["load_kg"] is None:
            payload["load_kg"] = None
        if reps_per_set is not None and set_count is not None:
            reps = int(reps_per_set)
            count = max(int(set_count), 1)
            payload["sets"] = [
                {"load_kg": payload["load_kg"], "reps": reps}
                for _ in range(count)
            ]
        else:
            payload["sets"] = _coerce_strength_sets(row)
    else:
        payload["sets"] = _coerce_strength_sets(row)

    return payload


def execute_save(mid, state_key, editor_key):
    """Commits all pending edits to the database and refreshes state."""
    df = st.session_state[state_key]
    state = st.session_state.get(editor_key, {})
    
    # 1. Process Deletions (using the markers defined in sync_editor_changes)
    for _, row in df[df["Change Log"] == "🔴"].iterrows():
        if pd.notna(row.get("id")): 
            models.delete_entry(row["id"])
            
    # 2. Process Updates
    for _, row in df[df["Change Log"] == "🟡"].iterrows():
        if pd.notna(row.get("id")):
            raw_val = row.get("value")
            if raw_val is None or (isinstance(raw_val, float) and pd.isna(raw_val)) or (isinstance(raw_val, str) and raw_val.strip() == ""):
                db_val = None  # "not measured"
            else:
                db_val = float(raw_val)

            payload = {
                "value": db_val,
                "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat(),
            }
            strength_payload = _coerce_strength_payload(row)
            if "load_kg" in row or "reps_per_set" in row or "set_count" in row:
                payload["load_kg"] = strength_payload.get("load_kg")
                payload["value"] = strength_payload.get("load_kg") if strength_payload.get("load_kg") is not None else db_val
                payload["sets"] = strength_payload.get("sets", [])
            elif "load_kg" in row:
                raw_load = row.get("load_kg")
                if raw_load is None or (isinstance(raw_load, float) and pd.isna(raw_load)) or (isinstance(raw_load, str) and raw_load.strip() == ""):
                    payload["load_kg"] = None
                else:
                    payload["load_kg"] = float(raw_load)
                    payload["value"] = payload["load_kg"]
            if "sets" in row and "reps_per_set" not in row and "set_count" not in row:
                payload["sets"] = _coerce_strength_sets(row)
            models.update_entry(row["id"], payload)
            
    # 3. Process New Rows
    for row in state.get("added_rows", []):
        if row.get("value") is not None or row.get("load_kg") is not None or row.get("reps_per_set") is not None or row.get("set_count") is not None:
            payload = {
                "value": float(row["value"]) if row.get("value") is not None else None,
                "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                "metric_id": mid,
            }
            strength_payload = _coerce_strength_payload(row)
            if "load_kg" in row or "reps_per_set" in row or "set_count" in row:
                payload["load_kg"] = strength_payload.get("load_kg")
                payload["value"] = strength_payload.get("load_kg") if strength_payload.get("load_kg") is not None else payload["value"]
                payload["sets"] = strength_payload.get("sets", [])
            elif "load_kg" in row:
                payload["load_kg"] = float(row.get("load_kg", 0.0)) if row.get("load_kg") is not None else None
            if "sets" in row and "reps_per_set" not in row and "set_count" not in row:
                payload["sets"] = row.get("sets") or []
            models.create_entry(payload)
    
    # --- FIX: RE-FETCH FRESH DATA ---
    # Bust the per-session cache before reloading data so the UI reflects deletions.
    cache_control.bump()
    # We clear the cache and fetch the updated dataset from the DB
    # Assuming your metric object is available or you just need the ID to re-fetch
    # If collect_data requires the full 'selected_metric' dict, you may need to pass it in
    fresh_dfe, _, _ = utils.collect_data({"id": mid}) 

    # 4. Clean up and update state with fresh data instead of empty DFs
    if editor_key in st.session_state:
        # Streamlit forbids setting widget state directly; remove it to reset.
        st.session_state.pop(editor_key, None)
    reset_editor_state(state_key, mid)
    if fresh_dfe is not None:
        st.session_state[f"saved_data_{mid}"] = fresh_dfe.copy()
        st.session_state[state_key] = fresh_dfe.assign(**{"Change Log": "", "Select": False})

    utils.finalize_action("Changes Saved Successfully!")
    st.rerun()
