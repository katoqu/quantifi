import streamlit as st
import pandas as pd
import models
import datetime as dt

@st.dialog("Confirm Changes")
def confirm_save_dialog(mid, editor_key):
    state_key = f"data_{mid}"
    df = st.session_state[state_key]
    state = st.session_state[editor_key]
    
    # Identify pending actions
    to_delete = df[df["Change Log"] == "🗑️ DELETED"]
    to_update = df[df["Change Log"].str.contains("📝", na=False)]
    to_add = state.get("added_rows", [])

    st.markdown(f"**🗑️ Deleting:** {len(to_delete)} | **📝 Updating:** {len(to_update)} | **➕ Adding:** {len(to_add)}")

    if st.button("Confirm & Push to Backend", type="primary", use_container_width=True):
        with st.spinner("Saving..."):
            # 1. Process Deletions
            for _, row in to_delete.iterrows():
                if pd.notna(row.get("id")):
                    models.delete_entry(row["id"])

            # 2. Process Edits
            for _, row in to_update.iterrows():
                rid = row.get("id")
                if pd.notna(rid):
                    payload = {
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
                    }
                    models.update_entry(rid, payload)

            # 3. Process Additions
            for row in to_add:
                if row.get("value") is not None:
                    models.create_entry({
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                        "metric_id": mid
                    })

            del st.session_state[state_key]
            st.success("Changes saved!")
            st.rerun()

def editable_metric_table(dfe, m_unit, mid):
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"
    
    # 1. Initialization
    if state_key not in st.session_state:
        df_init = dfe.sort_values("recorded_at", ascending=False).reset_index(drop=True)
        st.session_state[state_key] = df_init.assign(**{"Change Log": "", "Select": False})

    # 2. Define the callback
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

    # 3. Create the Filtered View
    full_draft_df = st.session_state[state_key]
    view_df = full_draft_df[full_draft_df['id'].isin(dfe['id'])]

    # 4. Display the Data Editor
    st.data_editor(
        view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("🗑️", help="Mark for deletion"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM, HH:mm"),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})"),
            "Change Log": st.column_config.TextColumn("Status", disabled=True),
            "id": None, "metric_id": None, "user_id": None, "created_at": None, "updated_at": None
        },
        key=editor_key,
        on_change=handle_change,
        use_container_width=True,
        hide_index=True
    )

    # 5. Action Buttons
    st.markdown("---")
    col_save, col_clear = st.columns([1, 1])
    
    with col_save:
        if st.button("💾 Save All Changes", type="primary", use_container_width=True):
            confirm_save_dialog(mid, editor_key)
            
    with col_clear:
        # Check draft status to enable/disable button
        has_changes = (st.session_state[state_key]["Change Log"] != "").any()
        
        if st.button("🧹 Clear All Changes", use_container_width=True, disabled=not has_changes):
            # Delete the current session draft to reset to original data
            del st.session_state[state_key]
            st.toast("Changes discarded.")
            st.rerun()