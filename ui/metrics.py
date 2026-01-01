import streamlit as st
import models
import utils

def show_create_metric(cats):
    """Refactored to handle unit definitions directly within the metric."""
    with st.expander("Add new metric", expanded=False):
        mn = st.text_input("Metric name (e.g., Bench Press)")
        
        col_u1, col_u2 = st.columns(2)
        with col_u1:
            unit_name = st.text_input("Unit name (e.g., kg, reps, miles)")
        with col_u2:
            unit_type = st.selectbox(
                "Data type", 
                options=["float", "integer", "integer_range"],
                index=0
            )

        # Only show range inputs if 'integer_range' is selected
        range_start, range_end = None, None
        if unit_type == "integer_range":
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min value", step=1, value=0)
            range_end = rcol2.number_input("Max value", step=1, value=10)

        cat_options = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in (cats or [])]
        cat_choice = st.selectbox(
            "Category", 
            [o[0] for o in cat_options], 
            format_func=lambda i: next((n for (_id, n) in cat_options if _id == i), "— none —")
        )

        if st.button("Create metric", type="primary") and mn.strip():
            name_norm = utils.normalize_name(mn)
            
            # Check for existing metrics
            existing_metrics = models.get_metrics() or []
            if any(m.get("name", "").lower() == name_norm for m in existing_metrics):
                st.info("Metric already exists (case-insensitive)")
            else:
                # Build the consolidated payload
                payload = {
                    "name": name_norm,
                    "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                    "unit_type": unit_type,
                    "range_start": range_start,
                    "range_end": range_end,
                    "category_id": cat_choice
                }
                
                models.create_metric(payload)
                st.cache_data.clear()
                st.success(f"Metric '{mn}' created successfully!")
                st.rerun()

def select_metric(metrics):
    """Simplified helper to select a metric without needing a separate unit_meta dictionary."""
    if not metrics:
        return None
    
    # We can now format the label directly because unit_name is in the metric object
    metric_idx = st.selectbox(
        "Select Metric", 
        options=list(range(len(metrics))), 
        format_func=lambda i: f"{metrics[i]['name'].title()} ({metrics[i].get('unit_name', 'No Unit')})"
    )
    
    return metrics[metric_idx]