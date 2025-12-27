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
        st.session_state[state_key] = df_init.assign(**{"Change Log": ""})

    # --- KEY FIX: Check if a new row already exists ---
    current_df = st.session_state[state_key]
    has_unsaved_new_row = current_df["Change Log"].str.contains("NEW ROW", na=False).any()

    def handle_change():
        state = st.session_state[editor_key]
        df = st.session_state[state_key]
        
        # Track Deletions
        for idx in state.get("deleted_rows", []):
            df.at[idx, "Change Log"] = "DELETED"

        # Track Edits
        for idx, changes in state.get("edited_rows", {}).items():
            logs = []
            for col, new_val in changes.items():
                old_val = df.at[idx, col]
                if str(old_val) != str(new_val):
                    logs.append(f"{col}: {old_val} → {new_val}")
                    df.at[idx, col] = new_val
            if logs:
                # Append to existing log if it's a NEW ROW, else replace
                current_log = df.at[idx, "Change Log"]
                new_log = " | ".join(logs)
                df.at[idx, "Change Log"] = f"{current_log} | {new_log}" if "NEW ROW" in current_log else new_log

        # Track Additions (Only if one isn't already present)
        if state.get("added_rows") and not has_unsaved_new_row:
            for row in state["added_rows"]:
                if any(v is not None for v in row.values()):
                    new_row = {
                        "recorded_at": row.get("recorded_at", dt.datetime.combine(dt.date.today(), dt.time(0, 0))),
                        "value": row.get("value"),
                        "Change Log": "NEW ROW"
                    }
                    st.session_state[state_key] = pd.concat([df, pd.DataFrame([new_row])], ignore_index=True)
                    # We break after one to ensure only one is added per cycle
                    break 

    # 1. Display the table
    st.data_editor(
        st.session_state[state_key],
        column_order=["recorded_at", "value", "Change Log"],
        column_config={
            "recorded_at": st.column_config.DatetimeColumn("Date", format="D MMM YYYY, HH:mm", required=True, default=dt.datetime.combine(dt.date.today(), dt.time(0, 0))),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})", required=True),
            "Change Log": st.column_config.TextColumn("Change Log", disabled=True, width="large")
        },
        key=editor_key,
        # --- KEY FIX: Disable dynamic rows if a new row is already pending ---
        num_rows="fixed" if has_unsaved_new_row else "dynamic",
        on_change=handle_change,
        hide_index=True,
        use_container_width=True
    )

    if has_unsaved_new_row:
        st.caption("⚠️ Save or Reset to add more rows.")

    # 2. Action Buttons
    col1, col2 = st.columns([1, 4])
    with col1:
        if st.button("Reset Changes", type="secondary"):
            del st.session_state[state_key]
            st.rerun()
    with col2:
        if st.button("Save to Backend", type="primary"):
            if st.session_state[state_key]["Change Log"].str.strip().any():
                confirm_save_dialog(mid)
            else:
                st.info("No changes to save.")
