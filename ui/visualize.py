import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import models
import numpy as np

# 1. Define the Dialog function outside the main logic
@st.dialog("Confirm Save")
def confirm_save_dialog(dfe, edited_df, mid):
    st.write("Are you sure you want to save these changes to the backend? This will create, update, or delete rows as shown.")
    
    if st.button("Yes, save changes"):
        with st.spinner("Saving changes to backend..."):
            # Make copies to avoid mutating originals
            orig = dfe.copy()
            new = edited_df.copy()

            # Ensure id column exists on both
            orig_ids = set(orig["id"].astype(str)) if "id" in orig.columns else set()
            new_ids = set(new["id"].dropna().astype(str)) if "id" in new.columns else set()

            # Deleted rows
            deleted = orig_ids - new_ids
            deleted_count = 0
            for rid in deleted:
                try:
                    models.delete_entry(rid)
                    deleted_count += 1
                except Exception as e:
                    st.error(f"Failed to delete {rid}: {e}")

            def _to_date_str(v):
                if pd.isna(v): return None
                return pd.to_datetime(v).date().isoformat()

            updated_count = 0
            created_count = 0

            for _, row in new.iterrows():
                rid = row.get("id") if "id" in new.columns else None
                payload = {
                    "value": None if pd.isna(row.get("value")) else float(row.get("value")),
                    "recorded_at": _to_date_str(row.get("recorded_at")),
                    "metric_id": mid
                }

                if pd.isna(rid) or rid is None:
                    try:
                        models.create_entry(payload)
                        created_count += 1
                    except Exception as e:
                        st.error(f"Failed to create entry: {e}")
                else:
                    orig_row = orig[orig["id"].astype(str) == str(rid)]
                    if not orig_row.empty:
                        orow = orig_row.iloc[0]
                        o_val = orow.get("value")
                        n_val = payload["value"]
                        o_date = _to_date_str(orow.get("recorded_at"))
                        
                        val_changed = (pd.isna(o_val) != pd.isna(n_val)) or (not pd.isna(o_val) and float(o_val) != n_val)
                        date_changed = o_date != payload["recorded_at"]

                        if val_changed or date_changed:
                            try:
                                models.update_entry(rid, payload)
                                updated_count += 1
                            except Exception as e:
                                st.error(f"Failed to update {rid}: {e}")
            
            st.success(f"Saved! Updated: {updated_count}, Created: {created_count}, Deleted: {deleted_count}")
            # Rerun to refresh the visualization and table with new data
            st.rerun()

def show_visualizations():
    st.header("Visualizations")
    
    # 1. Fetch Units and Metrics
    units = models.get_units() or []
    unit_lookup = {u["id"]: u["name"].title() for u in units}
    metrics = models.get_metrics() or []

    # 2. Filter Metrics with Entries
    selected_metric = st.selectbox("Select Metric to view", options=metrics,
        format_func=lambda m: m.get("name", "Unknown").title())

    mid = selected_metric.get("id")
    m_name = selected_metric.get("name", "Unknown").title()
    m_unit = unit_lookup.get(selected_metric.get("unit_id"), "Value")
    
    entries = models.get_entries(mid) or []
    if not entries:
        st.warning(f"No data entries found for {m_name}.")
        return
        
    # 3. Data Preparation
    dfe = pd.DataFrame(entries)
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    dfe = dfe.sort_values("recorded_at")

    # 4. Time Series Plot 
    avg_value = dfe["value"].mean()
    fig = go.Figure()

    # Smooth Fitted Line (Spline)
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4'),
        name="Trend"
    ))

    # Actual Data Points
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="markers", 
        marker=dict(color='blue', size=8),
        name="Entries"
    ))

    # Dotted Average Line
    fig.add_hline(
        y=avg_value, 
        line_dash="dot", 
        line_color="red", 
        annotation_text=f"Avg: {avg_value:.1f}", 
        annotation_position="bottom right"
    )

    # Dynamic Title and Axis
    fig.update_layout(
        title=f"Time Series: {m_name}",
        xaxis_title="Recorded date",
        yaxis_title=m_unit,
        height=400,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)

    # 6. Editable Table
    st.subheader("Edit Data")

    # Provide clear instructions for the dynamic row deletion UI
    st.info("💡 **To Delete:** Select row(s) using the checkbox on the left and press **Delete** on your keyboard or click the trash icon.")

    edited_df = st.data_editor(
        dfe,
        column_order=("recorded_at", "value"),
        column_config={
            "recorded_at": st.column_config.DatetimeColumn(
                "Date", 
                format="D MMM YYYY, HH:mm",
                help="This column is read-only."
            ),
            "value": st.column_config.NumberColumn(f"Value ({m_unit})"),
            "id": None 
        },
        # Only allow editing of the 'value' column
        disabled=["recorded_at"], 
        hide_index=True,
        use_container_width=True,
        # Enables the selection checkbox for adding/deleting rows
        num_rows="dynamic", 
        key="metric_editor"
    )

    # Trigger the Dialog
    if st.button("Save Changes"):
        confirm_save_dialog(dfe, edited_df, mid)