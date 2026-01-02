import streamlit as st
import pandas as pd
import utils
from datetime import timedelta
from ui import visualize
from logic import editor_handler

@st.dialog("Confirm Changes")
def _confirm_save_dialog(mid, editor_key, state_key):
    """
    Pops up a confirmation dialog showing a summary of pending changes.
    Must be defined before it is called by _render_editable_table.
    """
    summary = editor_handler.get_change_summary(state_key, editor_key)
    st.markdown(f"**🗑️ Deleting:** {summary['del']} | **📝 Updating:** {summary['upd']} | **➕ Adding:** {summary['add']}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            editor_handler.execute_save(mid, state_key, editor_key)
        st.success("Changes saved!")
        st.rerun()

def _render_editable_table(view_df, m_unit, mid, state_key):
    """Renders the data editor table with custom column configurations."""
    editor_key = f"editor_{mid}"
    
    st.data_editor(
        view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})"),
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
        },
        key=editor_key,
        on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
        use_container_width=True,
        hide_index=True
    )

    # Compact Action Row
    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save", type="primary", use_container_width=True):
            _confirm_save_dialog(mid, f"editor_{mid}", state_key)
    with col_clear:
        unsaved = editor_handler.has_unsaved_changes(state_key)
        if st.button("🧹 Clear", use_container_width=True, disabled=not unsaved):
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
    # 1. Collect raw data from DB
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    mid = selected_metric.get("id")
    state_key = f"data_{mid}"
    saved_key = f"saved_data_{mid}"
    
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        return

    # Initialize States
    if state_key not in st.session_state:
        st.session_state[state_key] = dfe.assign(**{"Change Log": "", "Select": False})
    if saved_key not in st.session_state:
        st.session_state[saved_key] = dfe.copy()

    abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)

    # --- UX STEP 1: COMPACT DATE FILTERS ---
    # Using an expander saves vertical space for the actual editor
    with st.expander("📅 Filter Date Range", expanded=False):
        col_start, col_end = st.columns(2)
        prev_start, prev_end = st.session_state.get(f"prev_date_{mid}", (abs_min, abs_max))
        start_date = col_start.date_input("Start", value=prev_start, key=f"start_date_{mid}")
        end_date = col_end.date_input("End", value=prev_end, key=f"end_date_{mid}")

    if editor_handler.is_date_conflict(mid, state_key):
        _render_conflict_warning(mid, state_key)
        return 

    if start_date <= end_date:
        # --- UX STEP 2: DATA TABLE FIRST ---
        # Users come here to edit; place the draft table at the top
        master_draft = st.session_state[state_key]
        d_temp_date = pd.to_datetime(master_draft['recorded_at']).dt.date
        d_mask = (d_temp_date >= start_date) & (d_temp_date <= end_date)
        table_view_df = master_draft.loc[d_mask].sort_values("recorded_at", ascending=False)

        # Use a fixed height so the table doesn't push the graph off-screen
        _render_editable_table(table_view_df, m_unit, mid, state_key) 
      
        # --- UX STEP 3: KPI & PLOT SECOND ---
        # Use saved data for visualization so it doesn't jump while editing
        saved_df = st.session_state[saved_key]
        s_temp_date = pd.to_datetime(saved_df['recorded_at']).dt.date
        s_mask = (s_temp_date >= start_date) & (s_temp_date <= end_date)
        graph_df = saved_df.loc[s_mask].sort_values("recorded_at")

        # Renders the compact KPI Bar + Plot from visualize.py
        visualize.show_visualizations(graph_df, m_unit, m_name) 
    else:
        st.error("Invalid Range: Start date must be before or equal to end date.")