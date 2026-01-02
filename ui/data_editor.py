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
    """
    summary = editor_handler.get_change_summary(state_key, editor_key)
    st.markdown(f"**🗑️ Deleting:** {summary['del']} | **📝 Updating:** {summary['upd']} | **➕ Adding:** {summary['add']}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            editor_handler.execute_save(mid, state_key, editor_key)
        st.success("Changes saved!")
        st.rerun()

def _render_editable_table(view_df, m_unit, mid, state_key, selected_metric):
    """
    Renders the data editor table with range-aware column configurations.
    Enforces min/max bounds directly in the UI based on metric type.
    """
    editor_key = f"editor_{mid}"
    
    # 1. Determine Range and Step constraints
    utype = selected_metric.get("unit_type", "float")
    is_range = utype == "integer_range"
    
    # Configure numeric bounds if applicable
    r_min = float(selected_metric.get("range_start", 0)) if is_range else None
    r_max = float(selected_metric.get("range_end", 10)) if is_range else None
    
    # Use step=1 for integers to prevent decimal noise
    step = 1 if (is_range or utype == "integer") else 0.1

    st.data_editor(
        view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️"),
            "recorded_at": st.column_config.DatetimeColumn(
                "Date", 
                format="D MMM, HH:mm",
                timezone="UTC" # Aligns with database/utils UTC logic
            ),
            "value": st.column_config.NumberColumn(
                f"Value ({m_unit})",
                min_value=r_min,
                max_value=r_max,
                step=step
            ),
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
        },
        key=editor_key,
        on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
        use_container_width=True,
        num_rows="dynamic",
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
    """
    Mobile-optimized data management with integrated range enforcement.
    Includes Null-safety for date comparisons.
    """
    # 1. Fetch fresh data and metadata
    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    mid = selected_metric.get("id")
    state_key = f"data_{mid}"
    saved_key = f"saved_data_{mid}"
    
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
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

    # --- COMPACT FILTER ROW ---
    with st.expander("📅 Filter Date Range", expanded=False):
        f_col1, f_col2 = st.columns(2)
        
        # Ensure we have valid dates from session state or fallback to database bounds
        default_start, default_end = st.session_state.get(f"prev_date_{mid}", (abs_min, abs_max))
        
        # We use standard keys but ensure the variables are populated
        start_date = f_col1.date_input("Start", value=default_start, key=f"start_date_{mid}")
        end_date = f_col2.date_input("End", value=default_end, key=f"end_date_{mid}")

    # 5. NULL-SAFE COMPARISON
    # This prevents the '<=' not supported between NoneType error
    if start_date is not None and end_date is not None:
        if start_date <= end_date:
            # CONFLICT HANDLING
            if editor_handler.is_date_conflict(mid, state_key):
                _render_conflict_warning(mid, state_key)
                return 

            # RENDER TABLE
            master_draft = st.session_state[state_key]
            d_mask = (pd.to_datetime(master_draft['recorded_at']).dt.date >= start_date) & \
                     (pd.to_datetime(master_draft['recorded_at']).dt.date <= end_date)
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