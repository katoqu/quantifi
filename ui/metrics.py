import streamlit as st
import models
import utils

def show_create_metric(cats):
    """
    Renders the form to create a new metric with merged unit data.
    """
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

        # Range inputs for specific unit types
        range_start, range_end = None, None
        if unit_type == "integer_range":
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min value", step=1, value=0)
            range_end = rcol2.number_input("Max value", step=1, value=10)

        # Category mapping for the dropdown
        cat_options = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in (cats or [])]
        cat_choice = st.selectbox(
            "Category", 
            [o[0] for o in cat_options], 
            format_func=lambda i: next((n for (_id, n) in cat_options if _id == i), "— none —")
        )

        if st.button("Create metric", type="primary") and mn.strip():
            name_norm = utils.normalize_name(mn)
            
            # Use the single-table payload for the merged model
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
            st.success(f"Metric '{mn}' created!")
            st.rerun()

def show_edit_metrics(metrics_list, cats):
    st.subheader("Metric Management")
    
    cat_options = {c["id"]: c["name"].title() for c in (cats or [])}
    opt_ids = list(cat_options.keys())

    for m in metrics_list:
        # Outer Expander is allowed
        with st.expander(f"⚙️ Settings: {m['name'].title()} ({m.get('unit_name', 'No Unit')})"):
            
            # 1. Standard Metadata
            new_name = st.text_input("Metric Name", value=m['name'], key=f"ed_nm_{m['id']}")
            new_unit = st.text_input("Unit Name", value=m.get('unit_name', ''), key=f"ed_un_{m['id']}")
            
            # 2. Category Assignment
            current_cat_id = m.get("category_id")
            new_cat_id = st.selectbox(
                "Category",
                options=opt_ids,
                format_func=lambda x: cat_options[x],
                index=opt_ids.index(current_cat_id) if current_cat_id in opt_ids else 0,
                key=f"ed_ct_{m['id']}"
            )

            # 3. Read-Only Info (As requested to prevent data invalidation)
            st.info(f"Type: **{m.get('unit_type')}** | Range: **{m.get('range_start')} - {m.get('range_end')}**")
            st.caption("To change data types or ranges, please create a new metric.")

            # 4. Save Changes
            if st.button("Update Metric", key=f"upd_sv_{m['id']}", type="primary"):
                payload = {
                    "name": utils.normalize_name(new_name),
                    "unit_name": utils.normalize_name(new_unit),
                    "category_id": new_cat_id
                }
                models.update_metric(m['id'], payload) #
                st.cache_data.clear() #
                st.success("Updated successfully!")
                st.rerun()

            # 5. Fixed Danger Zone (No nested expanders or status blocks)
            st.markdown("---")
            st.error("### ⚠️ Danger Zone")
            entry_count = models.get_entry_count(m['id']) #
            st.write(f"This metric has **{entry_count}** recorded entries.")
            
            # Confirmation logic using a checkbox to prevent accidental clicks
            confirm_del = st.checkbox(f"I want to delete '{m['name'].title()}'", key=f"conf_{m['id']}")
            
            if st.button(f"Delete Metric", key=f"del_{m['id']}", use_container_width=True, disabled=not confirm_del, type="secondary"):
                if entry_count > 0:
                    st.error("Cannot delete metric with existing data. Delete all entries in 'Edit Data' first.")
                else:
                    models.delete_metric(m['id']) #
                    st.cache_data.clear() #
                    st.success("Metric deleted.")
                    st.rerun()

def select_metric(metrics):
    """
    Standard selection helper for the dashboard and editor.
    """
    if not metrics:
        return None
    metric_idx = st.selectbox(
        "Select Metric", 
        options=list(range(len(metrics))), 
        format_func=lambda i: f"{metrics[i]['name'].title()} ({metrics[i].get('unit_name', 'No Unit')})"
    )
    return metrics[metric_idx]