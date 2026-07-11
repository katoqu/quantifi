import streamlit as st
import pandas as pd
import utils
from ui import visualize
from logic import editor_handler
from metric_policy import resolve_metric_policy

def _prepare_strength_data_for_visualization(df):
    """Prepares strength session data for visualization by aggregating session data."""
    if df.empty or "session_group" not in df.columns:
        return df
    
    # Group by session and aggregate the data
    aggregated_data = []
    session_groups = df.groupby("session_group")
    
    for session_time, session_df in session_groups:
        # Create a representative row for the session
        session_row = session_df.iloc[0].copy()
        
        # Aggregate set information
        session_row["set_count"] = len(session_df)
        session_row["reps_per_set"] = session_df["reps_per_set"].iloc[0] if not session_df["reps_per_set"].empty else 1
        
        # Create sets data structure for visualization
        sets_data = []
        for _, row in session_df.iterrows():
            sets_data.append({
                "load_kg": row["load_kg"],
                "reps": row["reps_per_set"]
            })
        
        session_row["sets"] = sets_data
        aggregated_data.append(session_row)
    
    return pd.DataFrame(aggregated_data)


def _consolidate_session_editors(state_key, base_editor_key, is_strength):
    """Consolidate changes from all session editors into the main editor state."""
    if not is_strength:
        return  # Only needed for strength sessions with multiple editors
    
    # Get the master draft dataframe
    if state_key not in st.session_state:
        return
    
    master_draft = st.session_state[state_key]
    
    # Find all session editor keys that start with base_editor_key + "_session_"
    session_editor_keys = [
        key for key in st.session_state.keys() 
        if key.startswith(f"{base_editor_key}_session_")
    ]
    
    if not session_editor_keys:
        return
    
    # Initialize consolidated editor state if it doesn't exist
    if base_editor_key not in st.session_state:
        st.session_state[base_editor_key] = {"edited_rows": {}, "added_rows": []}
    
    consolidated_state = st.session_state[base_editor_key]
    
    # Consolidate edited rows from all session editors
    for session_key in session_editor_keys:
        if session_key in st.session_state:
            session_state = st.session_state[session_key]
            if "edited_rows" in session_state:
                # Map session-local indices to master dataframe indices
                # The session key contains the session identifier
                session_id = session_key.replace(f"{base_editor_key}_session_", "")
                
                # Find the rows in master draft that belong to this session
                if "original_id" in master_draft.columns:
                    # Convert session_id to the same type as original_id
                    try:
                        session_id_converted = int(session_id)
                        session_rows = master_draft[master_draft["original_id"] == session_id_converted]
                    except ValueError:
                        session_rows = master_draft[master_draft["original_id"] == session_id]
                else:
                    # Fallback for timestamp-based sessions
                    session_rows = master_draft[master_draft["session_group"] == pd.to_datetime(session_id, unit='s').floor('1s')]
                
                if not session_rows.empty:
                    # Map session editor row indices to master dataframe indices
                    session_indices = session_rows.index
                    for session_row_idx, changes in session_state["edited_rows"].items():
                        if session_row_idx < len(session_indices):
                            master_idx = session_indices[session_row_idx]
                            consolidated_state["edited_rows"][master_idx] = changes
    
    # Update the main editor state
    st.session_state[base_editor_key] = consolidated_state


@st.dialog("Confirm Changes")
def _confirm_save_dialog(mid, editor_key, state_key):
    """Review changes before committing to the database."""
    summary = editor_handler.get_change_summary(state_key, editor_key)
    master_draft = st.session_state[state_key]
    
    st.markdown("### 📋 Review Edits")
    st.write(f"✅ **New:** {summary['add']} | 📝 **Edited:** {summary['upd']} | 🗑️ **Deleted:** {summary['del']}")
    st.divider()
    
    changes = master_draft[master_draft["Change Log"] != ""]
    if not changes.empty:
        # Check if this is a strength session with session grouping
        if "original_id" in changes.columns:
            # Group changes by original_id (session)
            session_groups = changes.groupby("original_id")
            for session_id, session_changes in session_groups:
                with st.container(border=True):
                    if session_changes["Change Log"].iloc[0] == "🔴":
                        st.markdown("**🔴 DELETING SESSION**")
                    else:
                        st.markdown("**🟡 UPDATED SESSION**")
                    
                    # Show session details
                    session_time = session_changes["recorded_at"].iloc[0]
                    session_load = session_changes["load_kg"].iloc[0] if not session_changes["load_kg"].empty else "N/A"
                    session_reps = session_changes["reps_per_set"].iloc[0] if "reps_per_set" in session_changes.columns and not session_changes["reps_per_set"].empty else "N/A"
                    total_sets = len(session_changes)
                    
                    st.write(f"**Load:** {session_load} kg | **Reps/set:** {session_reps} | **Sets:** {total_sets}")
                    st.caption(f"📅 {session_time.strftime('%d %b, %H:%M')}")
        elif "session_group" in changes.columns:
            # Group changes by session (fallback)
            session_groups = changes.groupby("session_group")
            for session_time, session_changes in session_groups:
                with st.container(border=True):
                    if session_changes["Change Log"].iloc[0] == "🔴":
                        st.markdown("**🔴 DELETING SESSION**")
                    else:
                        st.markdown("**🟡 UPDATED SESSION**")
                    
                    # Show session details
                    session_load = session_changes["load_kg"].iloc[0] if not session_changes["load_kg"].empty else "N/A"
                    session_reps = session_changes["reps_per_set"].iloc[0] if not session_changes["reps_per_set"].empty else "N/A"
                    total_sets = len(session_changes)
                    
                    st.write(f"**Load:** {session_load} kg | **Reps/set:** {session_reps} | **Sets:** {total_sets}")
                    st.caption(f"📅 {session_time.strftime('%d %b, %H:%M')}")
        else:
            # Regular non-strength metric changes
            for _, row in changes.iterrows():
                with st.container(border=True):
                    if row["Change Log"] == "🔴":
                        st.markdown("**🔴 DELETING ENTRY**")
                    else:
                        st.markdown("**🟡 UPDATED ENTRY**")
                    st.write(f"**Value:** {row['value']}")
                    st.caption(f"📅 {pd.to_datetime(row['recorded_at']).strftime('%d %b, %H:%M')}")
    
    if st.button("Confirm & Save", type="primary", use_container_width=True):
        editor_handler.execute_save(mid, state_key, editor_key)

def _render_editable_table(view_df, m_unit, mid, state_key, selected_metric):
    """Renders the interactive data editor table."""
    ui_view_df = view_df.reset_index(drop=True)
    editor_key = f"editor_{mid}"
    kind = selected_metric.get("metric_kind")
    utype = selected_metric.get("unit_type", "float")
    is_strength = kind == "strength_session"
    if kind in ("count", "score"):
        step = 1
    else:
        step = 1 if "integer" in utype else 0.1

    if is_strength:
        # Group rows by original_id (session) for strength metrics
        # Check if we have expanded sets or original data structure
        if "original_id" in ui_view_df.columns:
            session_groups = ui_view_df.groupby("original_id")
        else:
            # Fallback for non-expanded data
            ui_view_df["session_group"] = ui_view_df["recorded_at"].dt.floor("1s")
            session_groups = ui_view_df.groupby("session_group")
        
        # Sort sessions by recorded_at in descending order (latest first)
        sorted_sessions = sorted(session_groups, key=lambda x: x[1]["recorded_at"].iloc[0], reverse=True)
        
        for session_id, session_df in sorted_sessions:
            # Determine session time for header and key
            if "original_id" in session_df.columns:
                session_time = session_df["recorded_at"].iloc[0]
                session_header = f"📅 Session: {session_time.strftime('%d %b %Y, %H:%M')} ({len(session_df)} sets)"
                # Create unique key for this session using original_id
                session_editor_key = f"{editor_key}_session_{session_df['original_id'].iloc[0]}"
            else:
                # Fallback for timestamp-based grouping
                session_time = session_id  # session_id is already a timestamp in this case
                session_header = f"📅 Session: {session_time.strftime('%d %b %Y, %H:%M')} ({len(session_df)} sets)"
                # Create unique key for this session using timestamp
                session_editor_key = f"{editor_key}_session_{session_time.timestamp()}"
            
            with st.expander(session_header, expanded=True):
                # Show session-level information
                session_load = session_df["load_kg"].iloc[0] if not session_df["load_kg"].empty else "N/A"
                session_reps = session_df["reps_per_set"].iloc[0] if not session_df["reps_per_set"].empty else "N/A"
                total_sets = len(session_df)
                
                st.caption(f"Load: {session_load} kg | Reps/set: {session_reps} | Total sets: {total_sets}")
                
                # Sort sets by set_index to maintain proper order
                sorted_session_df = session_df.sort_values("set_index" if "set_index" in session_df.columns else "recorded_at")
                
                # Create mapping from session local index to master dataframe index
                session_to_master_index = session_df.index
                
                # Render the session rows
                st.data_editor(
                    sorted_session_df.reset_index(drop=True),
                    column_order=["Select", "recorded_at", "load_kg", "reps_per_set", "set_count", "Change Log"],
                    column_config={
                        "Select": st.column_config.CheckboxColumn("🗑️", width="small"),
                        "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
                        "load_kg": st.column_config.NumberColumn("Load (kg)", step=1.0),
                        "reps_per_set": st.column_config.NumberColumn("Reps/set", step=1, format="%d"),
                        "set_count": st.column_config.NumberColumn("Sets", step=1, format="%d", disabled=True),
                        "Change Log": st.column_config.TextColumn("Status", disabled=True),
                    },
                    key=session_editor_key,
                    on_change=lambda: editor_handler.sync_editor_changes(state_key, session_editor_key, session_to_master_index),
                    use_container_width=True,
                    num_rows="dynamic",
                    hide_index=True
                )
    else:
        column_order = ["Select", "recorded_at", "value", "Change Log"]
        column_config = {
            "Select": st.column_config.CheckboxColumn("🗑️", width="small"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "value": st.column_config.NumberColumn(f"{m_unit}", step=step),
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
        }

        st.data_editor(
            ui_view_df,
            column_order=column_order,
            column_config=column_config,
            key=editor_key,
            on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
            use_container_width=True,
            num_rows="dynamic",
            hide_index=True
        )

    c1, c2 = st.columns(2)
    if c1.button("💾 Save", type="primary", use_container_width=True):
        # Consolidate changes from all session editors into main editor state
        _consolidate_session_editors(state_key, editor_key, is_strength)
        _confirm_save_dialog(mid, editor_key, state_key)
    if c2.button("🧹 Reset", use_container_width=True, disabled=not editor_handler.has_unsaved_changes(state_key)):
        editor_handler.reset_editor_state(state_key, mid)
        st.rerun()

def _render_conflict_warning(mid, state_key):
    """Prevents data loss when changing filters with unsaved edits."""
    st.warning("⚠️ **Unsaved Changes!** Changing filters will discard edits.")
    c1, c2 = st.columns(2)
    if c1.button("Discard & Update", use_container_width=True):
        editor_handler.reset_editor_state(state_key, mid)
        st.rerun()
    if c2.button("Keep Editing", type="primary", use_container_width=True):
        editor_handler.revert_date_range(mid)
        st.rerun()
    st.stop()

def show_data_management_suite(selected_metric):
    """Main entry point for the metric editor."""
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    mid = selected_metric.get("id")
    state_key = f"data_{mid}"
    
    if dfe is None or dfe.empty:
        st.info("No data recorded yet.")
        return

    # Initialize states
    if state_key not in st.session_state or st.session_state[state_key].empty:
        st.session_state[state_key] = editor_handler.prepare_entry_editor_frame(
            dfe.assign(**{"Change Log": "", "Select": False}),
            metric_kind=selected_metric.get("metric_kind"),
        )
    if f"saved_data_{mid}" not in st.session_state:
        st.session_state[f"saved_data_{mid}"] = editor_handler.prepare_entry_editor_frame(
            dfe.copy(),
            metric_kind=selected_metric.get("metric_kind"),
        )

    # 1. Unified Filters & Navigation
    abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)
    days_diff = (pd.to_datetime(abs_max) - pd.to_datetime(abs_min)).days
    pill_options = ["Week"]
    if days_diff > 7:
        pill_options.append("Month")
    if days_diff > 180:
        pill_options.append("Year")
    pill_options.extend(["All", "Custom"])

    pill_key = f"pill_{mid}"
    if pill_key in st.session_state and st.session_state[pill_key] not in pill_options:
        del st.session_state[pill_key]

    default_val = "Month" if "Month" in pill_options else "Week"
    selection = st.segmented_control(label="", options=pill_options, default=default_val, key=pill_key)

    p_start, p_end = editor_handler.get_pill_range(selection, abs_min, abs_max)

    if selection == "Custom":
        f1, f2 = st.columns(2)
        start_date = f1.date_input("From", value=abs_min, key=f"start_date_{mid}")
        end_date = f2.date_input("To", value=abs_max, key=f"end_date_{mid}")
    else:
        start_date, end_date = p_start, p_end
        st.session_state[f"start_date_{mid}"] = start_date
        st.session_state[f"end_date_{mid}"] = end_date

    # 2. Table Logic
    if start_date and end_date:
        if editor_handler.is_date_conflict(mid, state_key):
            _render_conflict_warning(mid, state_key)
        
        master_draft = st.session_state[state_key]
        d_mask = (
            ((pd.to_datetime(master_draft['recorded_at']).dt.date >= start_date) & 
             (pd.to_datetime(master_draft['recorded_at']).dt.date <= end_date)) | 
            (master_draft["Change Log"] != "")
        )
        _render_editable_table(
            master_draft.loc[d_mask].sort_values("recorded_at", ascending=False), 
            m_unit, mid, state_key, selected_metric
        )

    # 3. Visualizations synced with the editor's pill selection
    st.divider()
    saved_df = st.session_state.get(f"saved_data_{mid}")
    
    # NEW DEFENSIVE CHECK: Ensure data exists before mask application
    if saved_df is not None and not saved_df.empty and 'recorded_at' in saved_df.columns:
        s_mask = (pd.to_datetime(saved_df['recorded_at']).dt.date >= start_date) & \
                 (pd.to_datetime(saved_df['recorded_at']).dt.date <= end_date)
        
        # For strength sessions, prepare data for visualization by aggregating session data
        viz_df = saved_df.loc[s_mask].sort_values("recorded_at")
        if selected_metric.get("metric_kind") == "strength_session":
            viz_df = _prepare_strength_data_for_visualization(viz_df)
        
        visualize.show_visualizations(
            viz_df, 
            m_unit, 
            m_name, 
            metric_kind=selected_metric.get("metric_kind"),
            unit_type=selected_metric.get("unit_type", "float"),
            range_start=selected_metric.get("range_start"),
            range_end=selected_metric.get("range_end"),
            higher_is_better=selected_metric.get("higher_is_better", True),
            show_pills=False, 
            external_range=selection,
            policy=resolve_metric_policy(
                selected_metric.get("name"),
                metric_id=str(selected_metric["id"]) if selected_metric.get("id") else None,
            ),
            metric_id=str(selected_metric["id"]) if selected_metric.get("id") else None,
        )
    else:
        st.info("No data available to visualize.")
