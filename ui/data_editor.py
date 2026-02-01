import streamlit as st
import pandas as pd
import utils
from ui import visualize
from logic import editor_handler

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
    utype = selected_metric.get("unit_type", "float")
    step = 1 if "integer" in utype else 0.1

    st.data_editor(
        ui_view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️", width="small"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "value": st.column_config.NumberColumn(f"{m_unit}", step=step),
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
        },
        key=editor_key,
        on_change=lambda: editor_handler.sync_editor_changes(state_key, editor_key, view_df.index),
        use_container_width=True,
        num_rows="dynamic",
        hide_index=True
    )

    c1, c2 = st.columns(2)
    if c1.button("💾 Save", type="primary", use_container_width=True):
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
    if state_key not in st.session_state:
        st.session_state[state_key] = dfe.assign(**{"Change Log": "", "Select": False})
    if f"saved_data_{mid}" not in st.session_state:
        st.session_state[f"saved_data_{mid}"] = dfe.copy()

    # 1. Filters & Navigation (Always Visible)
    abs_min, abs_max = editor_handler.get_date_bounds(dfe, mid)
    pill_options = ["Last Week", "Last Month", "Last Year", "All Time", "Custom"]
    selection = st.segmented_control(label = "", options=pill_options, default="Last Month", key=f"pill_{mid}")

    p_start, p_end = editor_handler.get_pill_range(selection, abs_min, abs_max)

    if selection == "Custom":
        f1, f2 = st.columns(2)
        start_date = f1.date_input("From", value=abs_min, key=f"start_date_{mid}")
        end_date = f2.date_input("To", value=abs_max, key=f"end_date_{mid}")
    else:
        start_date, end_date = p_start, p_end
        st.session_state[f"start_date_{mid}"] = start_date
        st.session_state[f"end_date_{mid}"] = end_date

    # 3. Table Logic (Previously inside the expander)
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

    # 4. Visualizations synced with filters
    st.divider()
    saved_df = st.session_state[f"saved_data_{mid}"]
    s_mask = (pd.to_datetime(saved_df['recorded_at']).dt.date >= start_date) & \
             (pd.to_datetime(saved_df['recorded_at']).dt.date <= end_date)
    visualize.show_visualizations(saved_df.loc[s_mask].sort_values("recorded_at"), m_unit, m_name)