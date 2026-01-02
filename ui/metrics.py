import streamlit as st
import models
import utils

def show_edit_metrics(metrics_list, cats):
    st.subheader("Metric Management")
    
    # Search with Type-ahead
    all_metric_names = [m['name'].title() for m in metrics_list]
    selected_search = st.selectbox(
        "🔍 Search and Focus Metric",
        options=["— Show All —"] + sorted(all_metric_names),
        index=0
    )
    
    cat_options = {c["id"]: c["name"].title() for c in (cats or [])}
    opt_ids = list(cat_options.keys())

    # Grouping and Filter Logic
    grouped = {}
    for m in metrics_list:
        cat_name = cat_options.get(m.get("category_id"), "Uncategorized")
        if selected_search == "— Show All —" or m['name'].lower() == selected_search.lower():
            grouped.setdefault(cat_name, []).append(m)

    for cat_name in sorted(grouped.keys(), key=lambda x: (x == "Uncategorized", x)):
        with st.expander(f"📁 {cat_name} ({len(grouped[cat_name])})", expanded=(selected_search != "— Show All —")):
            for m in grouped[cat_name]:
                _render_metric_editor_block(m, opt_ids, cat_options)

def _render_metric_editor_block(m, opt_ids, cat_options):
    with st.container(border=True):
        col_name, col_unit, col_cat = st.columns([2, 1, 1])
        new_name = col_name.text_input("Metric Name", value=m['name'], key=f"ed_nm_{m['id']}")
        new_unit = col_unit.text_input("Unit", value=m.get('unit_name', ''), key=f"ed_un_{m['id']}")
        
        select_opts = opt_ids + ["NEW_CAT"]
        new_cat_id = col_cat.selectbox(
            "Category", options=select_opts,
            format_func=lambda x: "✨ Create New..." if x == "NEW_CAT" else cat_options.get(x, "Uncategorized"),
            index=select_opts.index(m.get("category_id")) if m.get("category_id") in select_opts else 0,
            key=f"ed_ct_{m['id']}"
        )

        inline_cat_name = st.text_input("New Category Name", key=f"inline_cat_{m['id']}") if new_cat_id == "NEW_CAT" else None

        if st.button("💾 Update", key=f"upd_sv_{m['id']}", type="primary", use_container_width=True):
            target_cat_id = utils.ensure_category_id(new_cat_id, inline_cat_name)
            models.update_metric(m['id'], {
                "name": utils.normalize_name(new_name),
                "unit_name": utils.normalize_name(new_unit),
                "category_id": target_cat_id
            })
            st.cache_data.clear()
            st.rerun()

def show_create_metric(cats):
    with st.expander("➕ Add New Metric", expanded=False):
        mn = st.text_input("Metric name")
        col1, col2 = st.columns(2)
        unit_name = col1.text_input("Unit")
        unit_type = col2.selectbox("Type", options=["float", "integer", "integer_range"])

        cat_opts = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in (cats or [])] + [("NEW_CAT", "✨ Create New...")]
        cat_choice = st.selectbox("Category", [o[0] for o in cat_opts], format_func=lambda i: next((n for (_id, n) in cat_opts if _id == i), "— none —"))
        new_cat_name = st.text_input("New Category Name") if cat_choice == "NEW_CAT" else None

        if st.button("Create Metric", type="primary") and mn.strip():
            final_cat_id = utils.ensure_category_id(cat_choice, new_cat_name)
            models.create_metric({
                "name": utils.normalize_name(mn), "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                "unit_type": unit_type, "category_id": final_cat_id
            })
            st.cache_data.clear()
            st.rerun()

# Add this to metrics.py

def select_metric(metrics, index=0):
    if not metrics:
        return None
    
    metric_options = [utils.format_metric_label(m) for m in metrics]
    
    selected_label = st.selectbox(
        "Select Metric",
        options=metric_options,
        index=index, # Uses the index we passed from the URL logic
    )
    
    for m in metrics:
        if utils.format_metric_label(m) == selected_label:
            return m
    return None