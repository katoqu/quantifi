import streamlit as st
import pandas as pd
import utils
from datetime import timedelta
from ui import visualize
from logic import editor_handler

@st.dialog("Confirm Changes")
def confirm_save_dialog(mid, editor_key):
    """
    Displays a confirmation summary before pushing changes to the database.
    """
    state_key = f"data_{mid}"
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    
    # Identify specific change types for the summary
    to_delete = df[df["Change Log"] == "🗑️ DELETED"]
    to_update = df[df["Change Log"].str.contains("📝", na=False)]
    to_add = state.get("added_rows", [])

    st.markdown(f"**🗑️ Deleting:** {len(to_delete)} | **📝 Updating:** {len(to_update)} | **➕ Adding:** {len(to_add)}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            # Offload backend logic to the handler
            editor_handler.process_save_to_backend(mid, df, state, to_delete, to_update, to_add)
        
        st.success("Changes saved!")
        st.rerun()

def show_data_management_suite(selected_metric, unit_meta):
    """
    Main entry point for the 'Edit Data' page.
    """
    # Fetch fresh data for the metric
    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)
    mid = selected_metric.get("id")
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"
    date_picker_key = f"date_range_{mid}"
    
    if dfe is not None and not dfe.empty:
        # 1. Logic: Get boundaries and repair any corrupted date states
        abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)

        # 2. Logic: Handle unsaved change warnings before allowing date changes
        _handle_unsaved_conflicts(mid, state_key)

        # 3. UI: Render Date Input
        # We explicitly pass 'value' to force the widget to stay in Range Mode
        current_date_range = st.date_input(
            "Select range",
          #  value=st.session_state.get(date_picker_key),
            key=date_picker_key,
            min_value=abs_min,
            max_value=abs_max + timedelta(days=365)
        )

        # 4. Filter and Render with defensive type checking
        # This prevents the "cannot unpack non-iterable" error
        if isinstance(current_date_range, (tuple, list)) and len(current_date_range) == 2:
            start_date, end_date = current_date_range
            mask = (pd.to_datetime(dfe['recorded_at']).dt.date >= start_date) & \
                   (pd.to_datetime(dfe['recorded_at']).dt.date <= end_date)
            filtered_df = dfe.loc[mask].sort_values("recorded_at", ascending=False)

            # Show visualization
            visualize.show_visualizations(filtered_df, m_unit, m_name)
            st.divider()
            
            # Show Table Editor
            st.write("### ✏️ Edit Records")
            _render_editable_table(filtered_df, m_unit, mid, state_key, editor_key)
        else:
            # Display info if only one date is currently selected in the picker
            st.info("Select a start and end date on the calendar to filter records.")
    else:
        st.info("No data recorded for this metric yet.")


def _handle_unsaved_conflicts(mid, state_key):
    """Checks for conflicts but ignores partial (1-date) selections."""
    date_picker_key = f"date_range_{mid}"
    prev_date_key = f"prev_date_{mid}"
    
    if date_picker_key in st.session_state:
        current_val = st.session_state[date_picker_key]
        
        # GATING: Only logic-check or sync if we have a COMPLETED range
        if isinstance(current_val, (tuple, list)) and len(current_val) == 2:
            if current_val != st.session_state[prev_date_key] and \
               editor_handler.has_unsaved_changes(state_key):
                
                st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard edits.")
                c1, c2 = st.columns(2)
                
                if c1.button("Discard & Update", use_container_width=True):
                    if state_key in st.session_state: 
                        del st.session_state[state_key]
                    st.session_state[prev_date_key] = current_val
                    st.rerun()
                    
                if c2.button("Keep Editing", type="primary", use_container_width=True):
                    # Revert to the last known 2-date range
                    st.session_state[date_picker_key] = st.session_state[prev_date_key]
                    st.rerun()
                st.stop()
            else:
                # Sync: selection is complete and no conflicts, update backup
                st.session_state[prev_date_key] = current_val

def _render_editable_table(view_df_filtered, m_unit, mid, state_key, editor_key):
    """
    Renders the data editor and manages local session state for changes.
    """
    # Initialize the "Draft" state if it doesn't exist
    if state_key not in st.session_state:
        st.session_state[state_key] = view_df_filtered.assign(**{"Change Log": "", "Select": False})

    def handle_change():
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        # Map editor indices back to the source dataframe
        for idx, changes in state.get("edited_rows", {}).items():
            actual_idx = view_df.index[idx] 
            for col, val in changes.items():
                df.at[actual_idx, col] = val
                if col == "Select":
                    df.at[actual_idx, "Change Log"] = "🗑️ DELETED" if val else ""
                elif "🗑️" not in str(df.at[actual_idx, "Change Log"]):
                    df.at[actual_idx, "Change Log"] = "📝 Edited"

    # Filter the draft state to match the current date range view
    full_draft_df = st.session_state[state_key]
    view_df = full_draft_df[full_draft_df['id'].isin(view_df_filtered['id'])]

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
        on_change=handle_change,
        use_container_width=True,
        hide_index=True
    )

    col_save, col_clear = st.columns(2)
    with col_save:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            confirm_save_dialog(mid, editor_key)
    with col_clear:
        # Disable clear button if no changes are present
        has_edits = editor_handler.has_unsaved_changes(state_key)
        if st.button("🧹 Clear All Changes", use_container_width=True, disabled=not has_edits):
            del st.session_state[state_key]
            st.rerun()