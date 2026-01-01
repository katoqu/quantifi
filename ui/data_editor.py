import streamlit as st
import pandas as pd
import utils
from datetime import timedelta
from ui import visualize
from logic import editor_handler

def show_data_management_suite(selected_metric):
    """
    Refactored to pull unit metadata directly from the selected_metric object.
    """
    # 1. Collect data: The updated utils.collect_data now only needs the metric object
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    mid = selected_metric.get("id")
    state_key = f"data_{mid}"
    
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        return

    # Initialize Master Draft
    if state_key not in st.session_state:
        st.session_state[state_key] = dfe.assign(**{"Change Log": "", "Select": False})

    abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)

    # Render Date Input
    date_range = st.date_input(
        "Select range",
        key=f"date_range_{mid}",
        value=st.session_state.get(f"prev_date_{mid}", (abs_min, abs_max)),
        min_value=abs_min,
        max_value=abs_max + timedelta(days=365)
    )

    # Check for conflicts
    if editor_handler.is_date_conflict(mid, state_key):
        _render_conflict_warning(mid, state_key)
        return 

    # Filter View and Render
    if isinstance(date_range, (tuple, list)) and len(date_range) == 2:
        start_date, end_date = date_range
        master_draft = st.session_state[state_key]
        
        mask = (pd.to_datetime(master_draft['recorded_at']).dt.date >= start_date) & \
               (pd.to_datetime(master_draft['recorded_at']).dt.date <= end_date)
        view_df = master_draft.loc[mask].sort_values("recorded_at", ascending=False)

        visualize.show_visualizations(view_df, m_unit, m_name)
        st.divider()
        _render_editable_table(view_df, m_unit, mid, state_key)
    else:
        st.info("Please select a start and end date.")

def _render_editable_table(view_df, m_unit, mid, state_key):
    editor_key = f"editor_{mid}"
    
    st.data_editor(
        view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})"), # Uses direct unit name
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
        },
        key=editor_key,
        on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
        use_container_width=True,
        hide_index=True
    )
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            _confirm_save_dialog(mid, editor_key, state_key)
    with col_clear:
        unsaved = editor_handler.has_unsaved_changes(state_key)
        if st.button("🧹 Clear All Changes", use_container_width=True, disabled=not unsaved):
            editor_handler.reset_editor_state(state_key, mid)
            st.rerun()

@st.dialog("Confirm Changes")
def _confirm_save_dialog(mid, editor_key, state_key):
    summary = editor_handler.get_change_summary(state_key, editor_key)
    st.markdown(f"**🗑️ Deleting:** {summary['del']} | **📝 Updating:** {summary['upd']} | **➕ Adding:** {summary['add']}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            editor_handler.execute_save(mid, state_key, editor_key)
        st.success("Changes saved!")
        st.rerun()

def _render_conflict_warning(mid, state_key):
    st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard edits.")
    c1, c2 = st.columns(2)
    if c1.button("Discard & Update", use_container_width=True):
        editor_handler.reset_editor_state(state_key, mid)
        st.rerun()
    if c2.button("Keep Editing", type="primary", use_container_width=True):
        editor_handler.revert_date_range(mid) # Ensure this exists in logic
        st.rerun()
    st.stop()