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
    
    # 1. INITIALIZATION / RE-SYNC
    # If the state doesn't exist, OR if the database gave us different IDs 
    # (e.g. you added a new record via the 'Capture' form), we refresh the draft.
    if state_key not in st.session_state:
        df_init = dfe.sort_values("recorded_at").reset_index(drop=True)
        st.session_state[state_key] = df_init.assign(**{"Change Log": "", "Select": False})
    else:
        # Check if the database has new rows that our session state doesn't have yet
        current_ids = set(st.session_state[state_key]["id"].dropna())
        incoming_ids = set(dfe["id"].dropna())
        
        if not incoming_ids.issubset(current_ids):
            # This handles the case where you added an entry in the 'Capture' tab
            # We merge the new data while keeping existing 'Change Log' entries
            old_df = st.session_state[state_key]
            # Only add rows that aren't already in our draft
            new_rows = dfe[~dfe["id"].isin(old_df["id"])]
            if not new_rows.empty:
                new_rows = new_rows.assign(**{"Change Log": "", "Select": False})
                st.session_state[state_key] = pd.concat([old_df, new_rows]).sort_values("recorded_at").reset_index(drop=True)

    # 2. HANDLE EDITS (Remains the same)
    def handle_change():
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        for idx in state.get("deleted_rows", []):
            df.at[idx, "Change Log"] = "DELETED"
        for idx, changes in state.get("edited_rows", {}).items():
            for col, new_val in changes.items():
                df.at[idx, col] = new_val
                current_log = str(df.at[idx, "Change Log"])
                log_entry = f"{col} updated"
                if log_entry not in current_log:
                    df.at[idx, "Change Log"] = f"{current_log} | {log_entry}".strip(" | ")

    # 3. FILTERING THE VIEW (The Fix)
    # We always use the full session state as the source, 
    # but we filter it based on the dates currently active in the UI
    full_draft_df = st.session_state[state_key]
    
    # We need to make sure we filter against the IDs provided by the app.py filter
    view_df = full_draft_df[full_draft_df['id'].isin(dfe['id'])]

    # UI Buttons
    col_del, col_res = st.columns([1.5, 1])
    with col_del:
        if st.button("🗑️ Mark Selected for Deletion", use_container_width=True):
            # Use index mapping to update the master state
            st.session_state[state_key].loc[view_df[view_df["Select"] == True].index, "Change Log"] = "DELETED"
            st.rerun()

    with col_res:
        if st.button("Reset Draft", type="secondary", use_container_width=True):
            del st.session_state[state_key]
            st.rerun()

    # 4. DATA EDITOR
    st.data_editor(
        view_df,
        column_order=["Select", "recorded_at", "value", "Change Log"],
        column_config={
            "Select": st.column_config.CheckboxColumn("Select"),
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm", required=True),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})", required=True),
            "Change Log": st.column_config.TextColumn("Status / Change Log", disabled=True)
        },
        key=editor_key,
        on_change=handle_change,
        hide_index=True,
        use_container_width=True
    )

    # 5. SAVE LOGIC (Checks master state)
    if st.button("Save All Changes to Backend", type="primary", use_container_width=True):
        has_changes = full_draft_df["Change Log"].str.strip().any()
        has_additions = len(st.session_state[editor_key].get("added_rows", [])) > 0
        
        if has_changes or has_additions:
            confirm_save_dialog(mid, editor_key)
        else:
            st.info("No changes to save.")