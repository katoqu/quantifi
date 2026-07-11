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
    
    # Handle session-level grouping for strength metrics
    if "session_group" in df.columns or "original_id" in df.columns:
        _sync_session_level_changes(df)

def _sync_session_level_changes(df):
    """Ensures session-level consistency for strength metrics."""
    # Determine grouping column based on data structure
    group_col = "original_id" if "original_id" in df.columns else "session_group"
    
    # Group by session and ensure all sets in a session have the same change status
    session_groups = df.groupby(group_col)
    
    for session_id, session_df in session_groups:
        # If any set in the session is marked for deletion, mark all sets
        if (session_df["Change Log"] == "🔴").any():
            for idx in session_df.index:
                df.at[idx, "Change Log"] = "🔴"
                df.at[idx, "Select"] = True
        # If any set in the session is modified, mark all as modified for consistency
        elif (session_df["Change Log"] == "🟡").any():
            for idx in session_df.index:
                current_status = str(df.at[idx, "Change Log"])
                if current_status == "":
                    df.at[idx, "Change Log"] = "🟡"

def get_change_summary(state_key, editor_key):
    """Counts pending updates for the confirmation dialog."""
    df = st.session_state[state_key]
    state = st.session_state.get(editor_key, {})
    
    # For strength sessions, count unique sessions instead of individual rows
    if "original_id" in df.columns:
        # Use original_id for expanded sets
        deleted_sessions = df[df["Change Log"] == "🔴"]["original_id"].unique()
        updated_sessions = df[df["Change Log"] == "🟡"]["original_id"].unique()
        return {
            "del": len(deleted_sessions),
            "upd": len(updated_sessions),
            "add": len(state.get("added_rows", []))
        }
    elif "session_group" in df.columns:
        # Fallback for non-expanded strength data
        deleted_sessions = df[df["Change Log"] == "🔴"]["session_group"].unique()
        updated_sessions = df[df["Change Log"] == "🟡"]["session_group"].unique()
        return {
            "del": len(deleted_sessions),
            "upd": len(updated_sessions),
            "add": len(state.get("added_rows", []))
        }
    else:
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
    standard_cols = ["id", "recorded_at", "value", "Change Log", "Select", "session_group", "original_id", "set_index"]

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
        
        # Expand sets into individual rows for strength sessions
        if metric_kind == "strength_session":
            view_df = _expand_strength_sets_into_rows(view_df)
        else:
            # For backward compatibility, add session grouping for non-expanded strength data
            view_df["session_group"] = view_df["recorded_at"].dt.floor("1s")

    return view_df


def _expand_strength_sets_into_rows(df):
    """Expand strength session entries with sets arrays into individual set rows."""
    expanded_rows = []
    
    for idx, row in df.iterrows():
        sets = row.get("sets") or []
        if isinstance(sets, list) and sets:
            # Expand each set into its own row
            for set_idx, set_data in enumerate(sets):
                if isinstance(set_data, dict):
                    set_row = row.copy()
                    set_row["original_id"] = row["id"]  # Track original database entry
                    set_row["set_index"] = set_idx  # Track position in session
                    set_row["load_kg"] = set_data.get("load_kg", row.get("load_kg", row.get("value")))
                    set_row["reps_per_set"] = set_data.get("reps", row.get("reps_per_set", 1))
                    set_row["set_count"] = len(sets)  # Total sets in session
                    expanded_rows.append(set_row)
        else:
            # No sets data, keep as single row
            row_copy = row.copy()
            row_copy["original_id"] = row["id"]
            row_copy["set_index"] = 0
            expanded_rows.append(row_copy)
    
    if expanded_rows:
        expanded_df = pd.DataFrame(expanded_rows)
        # Reset index to ensure unique indices for each row
        expanded_df = expanded_df.reset_index(drop=True)
        # Add session grouping by original_id for proper session grouping
        expanded_df["session_group"] = expanded_df["original_id"]
        return expanded_df
    else:
        # Fallback to original dataframe
        df["session_group"] = df["recorded_at"].dt.floor("1s")
        return df


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


def _aggregate_expanded_sets_back(df):
    """Aggregate expanded set rows back into original database format."""
    if "original_id" not in df.columns:
        return df  # No expansion, return as-is
    
    # Group by original_id to reconstruct sessions
    aggregated_data = []
    session_groups = df.groupby("original_id")
    
    for original_id, session_df in session_groups:
        # Get the base row (first row has all the metadata)
        base_row = session_df.iloc[0].copy()
        
        # Reconstruct the sets array from individual rows
        sets = []
        for _, set_row in session_df.iterrows():
            set_data = {
                "load_kg": set_row["load_kg"],
                "reps": set_row["reps_per_set"]
            }
            sets.append(set_data)
        
        # Sort sets by set_index to maintain original order
        sets_sorted = sorted(sets, key=lambda x: session_df[session_df["load_kg"] == x["load_kg"]]["set_index"].iloc[0] if len(session_df[session_df["load_kg"] == x["load_kg"]]) > 0 else 0)
        
        base_row["sets"] = sets_sorted
        base_row["id"] = original_id  # Restore original ID
        aggregated_data.append(base_row)
    
    return pd.DataFrame(aggregated_data)


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
    # For strength sessions with expanded sets, delete by original_id
    if "original_id" in df.columns:
        # Group by original_id and delete entire sessions
        deletion_groups = df[df["Change Log"] == "🔴"].groupby("original_id")
        for original_id, session_rows in deletion_groups:
            # Get the original entry ID (all rows in session have same original_id)
            entry_id = session_rows["id"].iloc[0] if pd.notna(session_rows["id"].iloc[0]) else session_rows["original_id"].iloc[0]
            if pd.notna(entry_id):
                models.delete_entry(entry_id)
    elif "session_group" in df.columns:
        # Group by session and delete entire sessions (fallback)
        deletion_groups = df[df["Change Log"] == "🔴"].groupby("session_group")
        for session_time, session_rows in deletion_groups:
            for _, row in session_rows.iterrows():
                if pd.notna(row.get("id")): 
                    models.delete_entry(row["id"])
    else:
        # Regular deletion for non-strength metrics
        for _, row in df[df["Change Log"] == "🔴"].iterrows():
            if pd.notna(row.get("id")): 
                models.delete_entry(row["id"])
            
    # 2. Process Updates
    # For expanded sets, aggregate back to original format first
    if "original_id" in df.columns:
        df_to_process = _aggregate_expanded_sets_back(df)
    else:
        df_to_process = df
    
    for _, row in df_to_process[df_to_process["Change Log"] == "🟡"].iterrows():
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
