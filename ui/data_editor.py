import streamlit as st
import pandas as pd
import utils
from datetime import timedelta
from ui import visualize
from ui.capture import show_capture
from logic import editor_handler

@st.dialog("Confirm Changes")
def _confirm_save_dialog(mid, editor_key, state_key):
    """
    Dynamically generates descriptive logs including 'From -> To' transitions.
    """
    summary = editor_handler.get_change_summary(state_key, editor_key)
    master_draft = st.session_state[state_key]
    
    # Access the original baseline for comparison
    saved_key = f"saved_data_{mid}"
    baseline_df = st.session_state.get(saved_key)
    
    st.markdown("### 📋 Review Edits")
    
    # Optimized for Mobile: Vertical summary instead of 3 columns
    st.write(f"✅ **New:** {summary['add']}")
    st.write(f"📝 **Edited:** {summary['upd']}")
    st.write(f"🗑️ **Deleted:** {summary['del']}")
    
    st.divider()
    
    # 2. Detailed Card-based Change Log
    changes = master_draft[master_draft["Change Log"] != ""]
    if not changes.empty:
        for _, row in changes.iterrows():
            with st.container(border=True):
                if row["Change Log"] == "🔴":
                    st.markdown("**🔴 DELETING ENTRY**")
                    # Display original values so the user knows exactly what is being removed
                    st.write(f"**Value:** {row['value']}")
                    st.caption(f"📅 {pd.to_datetime(row['recorded_at']).strftime('%d %b, %H:%M')}")
                else:
                    # 1. RETRIEVE BASELINE DATA
                    from_val, from_ts = None, None
                    if baseline_df is not None and pd.notna(row.get('id')):
                        orig_row = baseline_df[baseline_df['id'] == row['id']]
                        if not orig_row.empty:
                            from_val = orig_row.iloc[0]['value']
                            from_ts = pd.to_datetime(orig_row.iloc[0]['recorded_at'])
                    
                    # 2. CAPTURE NEW DATA
                    new_val = row['value']
                    new_ts = pd.to_datetime(row['recorded_at'])
                    
                    st.markdown(f"**🟡 UPDATED ENTRY**")
                    
                    # 3. ONLY SHOW VALUE CHANGE IF MODIFIED
                    if from_val is not None and from_val != new_val:
                        st.write(f"**Value:** {from_val} ➡️ **{new_val}**")
                    elif from_val is None:
                        st.write(f"**Value:** {new_val} (New)")
                    
                    # 4. ONLY SHOW DATE CHANGE IF MODIFIED
                    if from_ts is not None and from_ts != new_ts:
                        st.write(f"**Date:** {from_ts.strftime('%d %b, %H:%M')} ➡️ **{new_ts.strftime('%d %b, %H:%M')}**")
                    else:
                        # If date didn't change, just show it as a static caption for context
                        st.caption(f"📅 {new_ts.strftime('%d %b, %H:%M')}")
    else:
        st.info("No changes to review.")
    if st.button("Confirm & Save", type="primary", use_container_width=True):
        editor_handler.execute_save(mid, state_key, editor_key)

def _render_editable_table(view_df, m_unit, mid, state_key, selected_metric):
    """
    Renders the table with the 'Status' emoji visible but narrow.
    """
    # 'drop=True' prevents the old index from becoming a new data column.
    ui_view_df = view_df.reset_index(drop=True)

    editor_key = f"editor_{mid}"
    utype = selected_metric.get("unit_type", "float")
    step = 1 if (utype in ["integer", "integer_range"]) else 0.1

    st.data_editor(
        ui_view_df,
        # 'Change Log' is visible as 'Status' but kept narrow
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️", width="40"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm", width="150"),
            "value": st.column_config.NumberColumn(f"{m_unit}", step=step, width="small"),
            "Change Log": st.column_config.TextColumn("Status", width="small", disabled=True),
        },
        key=editor_key,
        on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )

    # Action Row
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save", type="primary", use_container_width=True):
            _confirm_save_dialog(mid, f"editor_{mid}", state_key)
    with col_clear:
        if st.button("🧹 Reset", use_container_width=True, disabled=not editor_handler.has_unsaved_changes(state_key)):
            editor_handler.reset_editor_state(state_key, mid)
            st.rerun()

def _render_conflict_warning(mid, state_key):
    """Warns user if they change date filters while edits are pending."""
    st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard edits.")
    c1, c2 = st.columns(2)
    if c1.button("Discard & Update", use_container_width=True):
        editor_handler.reset_editor_state(state_key, mid)
        st.rerun()
    if c2.button("Keep Editing", type="primary", use_container_width=True):
        editor_handler.revert_date_range(mid)
        st.rerun()
    st.stop()

def show_data_management_suite(selected_metric):
    """
    Mobile-optimized data management.
    Fakes a single lightweight header by using the label of the first date input.
    """
    # 1. Fetch fresh data and metadata
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    mid = selected_metric.get("id")
    state_key = f"data_{mid}"
    st.session_state["last_active_mid"] = mid
        
    saved_key = f"saved_data_{mid}"
    
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        # NEW: Mobile-friendly call to action
        if st.button("➕ Add First Entry", type="primary", use_container_width=True):
                st.session_state["last_active_mid"] = mid  # Ensure the right metric is selected
                st.session_state["nav_to_record_trigger"] = True # Set a trigger instead of direct modification
                st.rerun()        
        return

    # 2. DETECT RANGE CHANGES
    range_ver_key = f"range_ver_{mid}"
    current_range = (selected_metric.get("range_start"), selected_metric.get("range_end"))
    
    if range_ver_key in st.session_state:
        if st.session_state[range_ver_key] != current_range:
            editor_handler.reset_editor_state(state_key, mid)
            st.session_state[range_ver_key] = current_range
            st.rerun()
    else:
        st.session_state[range_ver_key] = current_range

    # 3. INITIALIZE STATES
    if state_key not in st.session_state:
        st.session_state[state_key] = dfe.assign(**{"Change Log": "", "Select": False})
    
    if saved_key not in st.session_state:
        st.session_state[saved_key] = dfe.copy()

    # 4. FETCH BOUNDS WITH FALLBACKS
    abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)

    # --- FAKED LIGHTWEIGHT HEADER ---
    # We use the label of the first column as the "header" for both fields.
    # The second column gets a space " " as a label to keep the boxes aligned.
    f_col1, f_col2 = st.columns(2)
    
    default_start, default_end = st.session_state.get(f"prev_date_{mid}", (abs_min, abs_max))

    # Column 1 carries the actual descriptive label
    start_date = f_col1.date_input(
        "📅 Filter Date Range: From", 
        value=default_start, 
        key=f"start_date_{mid}"
    )
    
    # Column 2 uses a space to stay vertically level with Column 1
    end_date = f_col2.date_input(
        "To", 
        value=default_end, 
        key=f"end_date_{mid}"
    )

    # 5. NULL-SAFE COMPARISON & RENDERING
    if start_date is not None and end_date is not None:
        if start_date <= end_date:
            # CONFLICT HANDLING
            if editor_handler.is_date_conflict(mid, state_key):
                _render_conflict_warning(mid, state_key)
                return

            # RENDER TABLE
            master_draft = st.session_state[state_key]
            d_mask = (
                ((pd.to_datetime(master_draft['recorded_at']).dt.date >= start_date) & 
                (pd.to_datetime(master_draft['recorded_at']).dt.date <= end_date)) |
                (master_draft["Change Log"] != "") # This keeps edited rows visible regardless of filter
            )
            table_view_df = master_draft.loc[d_mask].sort_values("recorded_at", ascending=False)
            _render_editable_table(table_view_df, m_unit, mid, state_key, selected_metric)
            
            st.divider()

            # RENDER PLOT
            saved_df = st.session_state[saved_key]
            s_mask = (pd.to_datetime(saved_df['recorded_at']).dt.date >= start_date) & \
                     (pd.to_datetime(saved_df['recorded_at']).dt.date <= end_date)
            graph_df = saved_df.loc[s_mask].sort_values("recorded_at")

            visualize.show_visualizations(graph_df, m_unit, m_name)
        else:
            st.error("Invalid Range: Start date must be before or equal to end date.")
    else:
        st.warning("Please select a valid date range to view and edit data.")