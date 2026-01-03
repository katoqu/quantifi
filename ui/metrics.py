import streamlit as st
import models
import utils

@st.dialog("Confirm Metric Update")
def _confirm_metric_update_dialog(m, new_payload):
    """
    Summarizes changes and uses the centralized finalize_action for feedback.
    """
    st.markdown("### Review Changes")
    
    col1, col2 = st.columns(2)
    with col1:
        st.caption("Current")
        st.write(f"**Name:** {m['name'].title()}")
        st.write(f"**Unit:** {m.get('unit_name', 'None')}")
        if m.get("unit_type") == "integer_range":
            st.write(f"**Range:** {m.get('range_start')} - {m.get('range_end')}")
            
    with col2:
        st.caption("Proposed")
        st.write(f"**Name:** {new_payload['name'].title()}")
        st.write(f"**Unit:** {new_payload.get('unit_name', 'None')}")
        if m.get("unit_type") == "integer_range":
            st.write(f"**Range:** {new_payload.get('range_start')} - {new_payload.get('range_end')}")

    st.warning("Updating these settings will change how historical data is labeled.")

    if st.button("Confirm & Save", type="primary", use_container_width=True):
        with st.spinner("Updating..."):
            models.update_metric(m['id'], new_payload)
        
        # LOCATION 1: Using the new centralized helper
        utils.finalize_action(f"Updated: {new_payload['name'].title()}")

def show_edit_metrics(metrics_list, cats):
    st.subheader("Metric Management")
    
    all_metric_names = [m['name'].title() for m in metrics_list]
    selected_search = st.selectbox(
        "🔍 Search and Focus Metric",
        options=["— Show All —"] + sorted(all_metric_names),
        index=0
    )
    
    cat_options = {c["id"]: c["name"].title() for c in (cats or [])}
    opt_ids = list(cat_options.keys())

    grouped = {}
    for m in metrics_list:
        cat_name = cat_options.get(m.get("category_id"), "Uncategorized")
        if selected_search == "— Show All —" or m['name'].lower() == selected_search.lower():
            grouped.setdefault(cat_name, []).append(m)

    sorted_cat_names = sorted(grouped.keys(), key=lambda x: (x == "Uncategorized", x))

    for cat_name in sorted_cat_names:
        with st.expander(f"📁 {cat_name} ({len(grouped[cat_name])})", expanded=(selected_search != "— Show All —")):
            sorted_metrics = sorted(grouped[cat_name], key=lambda x: x['name'].lower())
            for m in sorted_metrics:
                _render_metric_editor_block(m, opt_ids, cat_options)

def _render_metric_editor_block(m, opt_ids, cat_options):
    with st.container(border=True):
        col_name, col_unit, col_cat = st.columns([2, 1, 1])
        new_name = col_name.text_input("Metric Name", value=m['name'], key=f"ed_nm_{m['id']}")
        new_unit = col_unit.text_input("Unit", value=m.get('unit_name', ''), key=f"ed_un_{m['id']}")
        
        # Sort category options alphabetically
        sorted_opt_ids = sorted(opt_ids, key=lambda x: cat_options.get(x, "").lower())
        select_opts = sorted_opt_ids + ["NEW_CAT"]
        
        new_cat_id = col_cat.selectbox(
            "Category", options=select_opts,
            format_func=lambda x: "✨ Create New..." if x == "NEW_CAT" else cat_options.get(x, "Uncategorized"),
            index=select_opts.index(m.get("category_id")) if m.get("category_id") in select_opts else 0,
            key=f"ed_ct_{m['id']}"
        )

        new_start = m.get("range_start", 0)
        new_end = m.get("range_end", 10)
        range_error = False
        error_msg = ""
        
        if m.get("unit_type") == "integer_range":
            rcol1, rcol2 = st.columns(2)
            db_start = m.get("range_start") if m.get("range_start") is not None else 0
            db_end = m.get("range_end") if m.get("range_end") is not None else 10
            
            new_start = rcol1.number_input("Min", value=int(db_start), step=1, key=f"rs_{m['id']}")
            new_end = rcol2.number_input("Max", value=int(db_end), step=1, key=f"re_{m['id']}")
            
            if new_start >= new_end:
                range_error = True
                error_msg = "Max must be strictly greater than Min."

            if not range_error:
                actual_min, actual_max = models.get_metric_value_bounds(m['id'])
                if actual_min is not None:
                    if new_start > actual_min:
                        range_error = True
                        error_msg = f"Cannot increase Min to {new_start}. Existing data has values as low as {actual_min}."
                    elif new_end < actual_max:
                        range_error = True
                        error_msg = f"Cannot decrease Max to {new_end}. Existing data has values as high as {actual_max}."

        if range_error:
            st.error(error_msg)

        inline_cat_name = st.text_input("New Category Name", key=f"inline_cat_{m['id']}") if new_cat_id == "NEW_CAT" else None

        if st.button("💾 Update", key=f"upd_sv_{m['id']}", type="primary", use_container_width=True, disabled=range_error):
            target_cat_id = utils.ensure_category_id(new_cat_id, inline_cat_name)
            
            payload = {
                "name": utils.normalize_name(new_name),
                "unit_name": utils.normalize_name(new_unit),
                "category_id": target_cat_id
            }
            
            if m.get("unit_type") == "integer_range":
                payload["range_start"] = new_start
                payload["range_end"] = new_end

            # Trigger the dialog instead of direct save
            _confirm_metric_update_dialog(m, payload)

def show_create_metric(cats):
    with st.expander("➕ Add New Metric", expanded=False):
        mn = st.text_input("Metric name")
        col1, col2 = st.columns(2)
        unit_name = col1.text_input("Unit")
        unit_type = col2.selectbox("Type", options=["float", "integer", "integer_range"])

        range_start, range_end = 0, 10
        range_error = False
        if unit_type == "integer_range":
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min Value", value=0, step=1)
            range_end = rcol2.number_input("Max Value", value=10, step=1)
            if range_start >= range_end:
                st.error("Max must be greater than Min")
                range_error = True

        sorted_cats = sorted(cats, key=lambda x: x["name"].lower()) if cats else []
        cat_opts = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in sorted_cats] + [("NEW_CAT", "✨ Create New...")]
        cat_choice = st.selectbox("Category", [o[0] for o in cat_opts], format_func=lambda i: next((n for (_id, n) in cat_opts if _id == i), "— none —"))
        new_cat_name = st.text_input("New Category Name") if cat_choice == "NEW_CAT" else None

        if st.button("Create Metric", type="primary", disabled=range_error) and mn.strip():
            final_cat_id = utils.ensure_category_id(cat_choice, new_cat_name)
            
            payload = {
                "name": utils.normalize_name(mn), 
                "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                "unit_type": unit_type, 
                "category_id": final_cat_id
            }
            
            if unit_type == "integer_range":
                payload["range_start"] = range_start
                payload["range_end"] = range_end

            models.create_metric(payload)
            
            # LOCATION 2: Centralized toast and rerun
            utils.finalize_action(f"Created: {mn.strip().title()}")

def select_metric(metrics, target_id=None): # Changed index to target_id
    if not metrics:
        return None
    
    # 1. Sort the metrics first so the list matches the UI
    sorted_metrics = sorted(metrics, key=lambda x: x.get("name", "").lower())
    metric_options = [utils.format_metric_label(m) for m in sorted_metrics]
    
    # 2. Find the correct index based on the target_id (if provided)
    default_index = 0
    if target_id:
        for i, m in enumerate(sorted_metrics):
            if m['id'] == target_id:
                default_index = i
                break
    
    selected_label = st.selectbox(
        "Select Metric",
        options=metric_options,
        index=default_index,
    )
    
    for m in sorted_metrics:
        if utils.format_metric_label(m) == selected_label:
            return m
    return None