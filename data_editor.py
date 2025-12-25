import streamlit as st
import pandas as pd
import models

@st.dialog("Confirm Save")
def confirm_save_dialog(mid):
    st.write("Are you sure you want to save changes to the backend?")
    if st.button("Yes, save changes"):
        with st.spinner("Saving..."):
            df = st.session_state[f"data_{mid}"]
            
            # Process Deletions
            deleted = df[df["Change Log"].str.contains("DELETED", na=False)]
            for rid in deleted["id"].dropna():
                models.delete_entry(rid)

            # Process Upserts (Active rows only)
            active = df[~df["Change Log"].str.contains("DELETED", na=False)]
            for _, row in active.iterrows():
                payload = {
                    "value": float(row["value"]) if pd.notna(row["value"]) else None,
                    "recorded_at": pd.to_datetime(row["recorded_at"]).isoformat() if pd.notna(row["recorded_at"]) else None,
                    "metric_id": mid
                }
                # Create if no ID, otherwise Update
                models.update_entry(row["id"], payload) if pd.notna(row.get("id")) else models.create_entry(payload)

            del st.session_state[f"data_{mid}"]
            st.success("Saved!"); st.rerun()

def editable_metric_table(dfe, m_unit, mid):
    state_key, editor_key = f"data_{mid}", f"editor_{mid}"

    if state_key not in st.session_state:
        # 1. Sort by date and reset the index to provide a stable, clean order for the editor
        df_init = dfe.sort_values("recorded_at").reset_index(drop=True)
        st.session_state[state_key] = df_init.assign(**{"Change Log": ""})

    def handle_change():
        # Get the delta from the editor and the current state
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        
        # A. Handle Deletions (uses stable integer index)
        for idx in state.get("deleted_rows", []):
            df.at[idx, "Change Log"] = f"{df.at[idx, 'Change Log']} | DELETED".strip(" | ")

        # B. Handle Edits
        for idx, changes in state.get("edited_rows", {}).items():
            logs = []
            for col, new_val in changes.items():
                old_val = df.at[idx, col]
                if str(old_val) != str(new_val):
                    logs.append(f"{col}: {old_val} → {new_val}")
                    df.at[idx, col] = new_val # Commit change to state
            
            if logs:
                df.at[idx, "Change Log"] = f"{df.at[idx, 'Change Log']} | {' | '.join(logs)}".strip(" | ")

        # C. Handle Additions
        if state.get("added_rows"):
            new_rows = pd.DataFrame(state["added_rows"]).assign(**{"Change Log": "NEW ROW"})
            st.session_state[state_key] = pd.concat([df, new_rows], ignore_index=True)

    # Display the editor
    st.data_editor(
        st.session_state[state_key],
        column_order=["recorded_at", "value", "Change Log"],
        column_config={
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm"),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})"),
            "Change Log": st.column_config.TextColumn("Change Log", disabled=True, width="large")
        },
        key=editor_key,
        on_change=handle_change,
        hide_index=True,
        use_container_width=True
    )

    if st.button("Save Changes"):
        confirm_save_dialog(mid)