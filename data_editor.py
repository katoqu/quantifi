import streamlit as st
import pandas as pd
import models
import datetime as dt

@st.dialog("Confirm Save")
def confirm_save_dialog(mid):
    st.write("Are you sure you want to push all recorded changes to the backend?")
    if st.button("Yes, save changes", type="primary"):
        with st.spinner("Saving..."):
            df = st.session_state[f"data_{mid}"]
            
            # 1. Process Deletions
            deleted = df[df["Change Log"].str.contains("DELETED", na=False)]
            for rid in deleted["id"].dropna():
                models.delete_entry(rid)

            # 2. Process Upserts
            active = df[~df["Change Log"].str.contains("DELETED", na=False)]
            for idx, row in active.iterrows():
                if not row["Change Log"]:
                    continue

                is_new_row = pd.isna(row.get("id")) or "NEW ROW" in str(row.get("Change Log"))
                
                if not is_new_row:
                    payload = {
                        "value": float(row["value"]),
                        "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat()
                    }
                    models.update_entry(row["id"], payload)
                else:
                    if pd.notna(row["value"]) and pd.notna(row["recorded_at"]):
                        payload = {
                            "value": float(row["value"]),
                            "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat(),
                            "metric_id": mid
                        }
                        models.create_entry(payload)

            del st.session_state[f"data_{mid}"]
            st.success("Changes saved successfully!")
            st.rerun()

def editable_metric_table(dfe, m_unit, mid):
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"

    if state_key not in st.session_state:
        df_init = dfe.sort_values("recorded_at").reset_index(drop=True)
        # Add Change Log and a Select column for UI-based deletion
        st.session_state[state_key] = df_init.assign(**{"Change Log": "", "Select": False})

    def handle_change():
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        
        # Track Native Deletions (Keyboard backspace/delete)
        for idx in state.get("deleted_rows", []):
            df.at[idx, "Change Log"] = "DELETED"

        # Track Edits
        for idx, changes in state.get("edited_rows", {}).items():
            for col, new_val in changes.items():
                old_val = df.at[idx, col]
                if str(old_val) != str(new_val):
                    df.at[idx, col] = new_val
                    # Update log
                    current_log = str(df.at[idx, "Change Log"])
                    log_entry = f"{col} updated"
                    if log_entry not in current_log:
                        df.at[idx, "Change Log"] = f"{current_log} | {log_entry}".strip(" | ")

        # Track Multiple Additions
        added = state.get("added_rows", [])
        if added:
            new_rows_list = []
            for row in added:
                new_rows_list.append({
                    "recorded_at": row.get("recorded_at", dt.datetime.now()),
                    "value": row.get("value"),
                    "Change Log": "NEW ROW",
                    "Select": False
                })
            st.session_state[state_key] = pd.concat([df, pd.DataFrame(new_rows_list)], ignore_index=True)

    # UI Buttons for Deletion and Reset
    col_del, col_res, col_save = st.columns([1.5, 1, 2])
    
    with col_del:
        if st.button("🗑️ Mark Selected for Deletion", use_container_width=True):
            df = st.session_state[state_key]
            # Any row where 'Select' is True gets marked for deletion
            df.loc[df["Select"] == True, "Change Log"] = "DELETED"
            df["Select"] = False # Uncheck boxes after marking
            st.session_state[state_key] = df
            st.rerun()

    with col_res:
        if st.button("Reset", type="secondary", use_container_width=True):
            del st.session_state[state_key]
            st.rerun()

    # 1. Display the table
    st.data_editor(
        st.session_state[state_key],
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("Select", help="Check to mark for deletion"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm", required=True),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})", required=True),
            "Change Log": st.column_config.TextColumn("Change Log", disabled=True)
        },
        key=editor_key,
        num_rows="dynamic", # Allow adding multiple rows
        on_change=handle_change,
        hide_index=True,
        use_container_width=True
    )

    # 2. Final Save Button
    if st.button("Save All Changes to Backend", type="primary", use_container_width=True):
        if st.session_state[state_key]["Change Log"].str.strip().any():
            confirm_save_dialog(mid)
        else:
            st.info("No changes to save.")