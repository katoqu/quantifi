import streamlit as st
import pandas as pd
import models
import datetime as dt

@st.dialog("Confirm Save")
def confirm_save_dialog(mid, editor_key):
    st.write("Are you sure you want to push all recorded changes to the backend?")
    if st.button("Yes, save changes", type="primary"):
        with st.spinner("Saving..."):
            state = st.session_state[editor_key]
            df = st.session_state[f"data_{mid}"]
            
            # 1. Process Deletions (Native and UI-marked)
            deleted_indices = state.get("deleted_rows", [])
            for idx in deleted_indices:
                rid = df.iloc[idx].get("id")
                if pd.notna(rid): models.delete_entry(rid)
                
            ui_deleted = df[df["Change Log"] == "DELETED"]
            for rid in ui_deleted["id"].dropna():
                models.delete_entry(rid)

            # 2. Process Edits (Rows marked in Change Log)
            for idx, row in df.iterrows():
                if "updated" in str(row.get("Change Log", "")):
                    rid = row.get("id")
                    if pd.notna(rid):
                        payload = {
                            "value": float(row["value"]),
                            "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
                        }
                        models.update_entry(rid, payload)

            # 3. Process Multiple Additions
            for row in state.get("added_rows", []):
                if row.get("value") is not None:
                    models.create_entry({
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row.get("recorded_at", dt.datetime.now())).isoformat(),
                        "metric_id": mid
                    })

            del st.session_state[f"data_{mid}"]
            st.success("Changes saved successfully!")
            st.rerun()

def editable_metric_table(dfe, m_unit, mid):
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"

    if state_key not in st.session_state:
        df_init = dfe.sort_values("recorded_at").reset_index(drop=True)
        # Reintroducing the Change Log column
        st.session_state[state_key] = df_init.assign(**{"Change Log": "", "Select": False})

    def handle_change():
        """Tracks edits and native deletions in the Change Log."""
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        
        # Track Native Deletions
        for idx in state.get("deleted_rows", []):
            df.at[idx, "Change Log"] = "DELETED"

        # Track Edits specifically for the Change Log
        for idx, changes in state.get("edited_rows", {}).items():
            for col, new_val in changes.items():
                # Update the value in our session state DF
                df.at[idx, col] = new_val
                # Update the log string
                current_log = str(df.at[idx, "Change Log"])
                log_entry = f"{col} updated"
                if log_entry not in current_log:
                    df.at[idx, "Change Log"] = f"{current_log} | {log_entry}".strip(" | ")

    # UI Buttons
    col_del, col_res = st.columns([1.5, 1])
    with col_del:
        if st.button("🗑️ Mark Selected for Deletion", use_container_width=True):
            st.session_state[state_key].loc[st.session_state[state_key]["Select"] == True, "Change Log"] = "DELETED"
            st.rerun()

    with col_res:
        if st.button("Reset", type="secondary", use_container_width=True):
            del st.session_state[state_key]
            st.rerun()

    # Re-enabled on_change for real-time logging of edits
    st.data_editor(
        st.session_state[state_key],
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("Select"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm", required=True),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})", required=True),
            "Change Log": st.column_config.TextColumn("Status / Change Log", disabled=True)
        },
        key=editor_key,
        num_rows="dynamic",
        on_change=handle_change,
        hide_index=True,
        use_container_width=True
    )

    if st.button("Save All Changes to Backend", type="primary", use_container_width=True):
        # Trigger save if there are edits in the DF or pending additions in the editor state
        has_changes = st.session_state[state_key]["Change Log"].str.strip().any()
        has_additions = len(st.session_state[editor_key].get("added_rows", [])) > 0
        
        if has_changes or has_additions:
            confirm_save_dialog(mid, editor_key)
        else:
            st.info("No changes to save.")