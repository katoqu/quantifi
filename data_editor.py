import streamlit as st
import pandas as pd
import models
import utils
import datetime as dt
from datetime import timedelta
from ui import visualize

@st.dialog("Confirm Changes")
def confirm_save_dialog(mid, editor_key):
    state_key = f"data_{mid}"
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    
    to_delete = df[df["Change Log"] == "🗑️ DELETED"]
    to_update = df[df["Change Log"].str.contains("📝", na=False)]
    to_add = state.get("added_rows", [])

    st.markdown(f"**🗑️ Deleting:** {len(to_delete)} | **📝 Updating:** {len(to_update)} | **➕ Adding:** {len(to_add)}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            # logic from
            for _, row in to_delete.iterrows():
                if pd.notna(row.get("id")):
                    models.delete_entry(row["id"])

            for _, row in to_update.iterrows():
                rid = row.get("id")
                if pd.notna(rid):
                    payload = {
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
                    }
                    models.update_entry(rid, payload)

            for row in to_add:
                if row.get("value") is not None:
                    models.create_entry({
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                        "metric_id": mid
                    })
        
        # Clear cache and state and rerun 
            st.cache_data.clear()
            del st.session_state[state_key]
            st.success("Changes saved!")
            st.rerun()

def show_data_management_suite(selected_metric, unit_meta):

    #Fetch fresh data for the metric
    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)
    mid = selected_metric.get("id")
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"
    
    # 1. State Protection Logic
    has_unsaved_changes = False
    if state_key in st.session_state:
        has_unsaved_changes = (st.session_state[state_key]["Change Log"] != "").any()

    # 2. Date Filter Logic (Moved from app.py)
    if dfe is not None and not dfe.empty:
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'])
        abs_min = dfe['recorded_at'].min().date()
        abs_max = dfe['recorded_at'].max().date()

        date_picker_key = f"date_range_{mid}"
        prev_date_key = f"prev_date_{mid}"

        # 2. REACTIVE DATE LOGIC:
        # If the data boundaries have changed (e.g. a new value was captured), 
        # reset the range to include the new data.
        if prev_date_key in st.session_state:
            stored_min, stored_max = st.session_state[prev_date_key]
            # If the actual data now exists outside the stored range, expand it
            if abs_min < stored_min or abs_max > stored_max:
                st.session_state[prev_date_key] = (abs_min, abs_max)
                if date_picker_key in st.session_state:
                    st.session_state[date_picker_key] = (abs_min, abs_max)
        else:
            # First time initialization
            st.session_state[prev_date_key] = (abs_min, abs_max)
            st.session_state[date_picker_key] = (abs_min, abs_max)
        
        # Conflict Check
        if date_picker_key in st.session_state:
            current_ui_val = st.session_state[date_picker_key]
            if current_ui_val != st.session_state[prev_date_key] and has_unsaved_changes:
                st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard edits.")
                c1, c2 = st.columns(2)
                if c1.button("Discard & Update", use_container_width=True):
                    if state_key in st.session_state: del st.session_state[state_key]
                    st.session_state[prev_date_key] = current_ui_val
                    st.rerun()
                if c2.button("Keep Editing", type="primary", use_container_width=True):
                    st.session_state[date_picker_key] = st.session_state[prev_date_key]
                    st.rerun()
                st.stop()
            else:
                st.session_state[prev_date_key] = current_ui_val

        if date_picker_key not in st.session_state:
            st.session_state[date_picker_key] = st.session_state[prev_date_key]

        # Render Date Input
        current_date_range = st.date_input(
            "Select range",
            key=date_picker_key,
            min_value=abs_min,
            max_value=abs_max + timedelta(days=365)
        )

        # 3. Filter and Render
        if isinstance(current_date_range, tuple) and len(current_date_range) == 2:
            start_date, end_date = current_date_range
            mask = (dfe['recorded_at'].dt.date >= start_date) & (dfe['recorded_at'].dt.date <= end_date)
            filtered_df = dfe.loc[mask].sort_values("recorded_at", ascending=False)

            # Show visualization
            visualize.show_visualizations(filtered_df, m_unit, m_name)
            st.divider()
            
            # Show Table Editor
            st.write("### ✏️ Edit Records")
            _render_editable_table(filtered_df, m_unit, mid, state_key, editor_key)
        else:
            st.info("Select a date range to begin.")
    else:
        st.info("No data recorded for this metric yet.")

def _render_editable_table(view_df_filtered, m_unit, mid, state_key, editor_key):
    """Internal helper to render the data editor."""
    # Initialization
    if state_key not in st.session_state:
        st.session_state[state_key] = view_df_filtered.assign(**{"Change Log": "", "Select": False})

    def handle_change():
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        for idx, changes in state.get("edited_rows", {}).items():
            actual_idx = view_df.index[idx] 
            for col, val in changes.items():
                df.at[actual_idx, col] = val
                if col == "Select":
                    df.at[actual_idx, "Change Log"] = "🗑️ DELETED" if val else ""
                elif "🗑️" not in str(df.at[actual_idx, "Change Log"]):
                    df.at[actual_idx, "Change Log"] = "📝 Edited"

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
        has_changes = (st.session_state[state_key]["Change Log"] != "").any()
        if st.button("🧹 Clear All Changes", use_container_width=True, disabled=not has_changes):
            del st.session_state[state_key]
            st.rerun()