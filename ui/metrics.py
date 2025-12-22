import streamlit as st
import models
import utils

def show_create_metric(cats, units):
    with st.expander("Add metric"):
        mn = st.text_input("Metric name")
        cat_options = [(None, "— none —")] + [(c["id"], c["name"].title()) for c in (cats or [])]
        unit_options = [(None, "— none —")] + [(u["id"], u["name"].title()) for u in (units or [])]
        cat_choice = st.selectbox("Category", [o[0] for o in cat_options], format_func=lambda i: next((n for (_id, n) in cat_options if _id == i), "— none —"))
        unit_choice = st.selectbox("Unit", [o[0] for o in unit_options], format_func=lambda i: next((n for (_id, n) in unit_options if _id == i), "— none —"))
        if st.button("Create metric") and mn.strip():
            name_norm = utils.normalize_name(mn)
            existing_metrics = models.get_metrics() or []
            if any(m.get("name", "").lower() == name_norm for m in existing_metrics):
                st.info("Metric already exists (case-insensitive)")
            else:
                payload = {"name": name_norm}
                if cat_choice:
                    payload["category_id"] = cat_choice
                if unit_choice:
                    payload["unit_id"] = unit_choice
                models.create_metric(payload)
                st.success("Metric created")

def select_metric(metrics, cats, units):
    if not metrics:
        return None, None, None
    cat_map = {c["id"]: c["name"].title() for c in (cats or [])}
    unit_map = {u["id"]: u["name"].title() for u in (units or [])}
    unit_meta = {u["id"]: u for u in (units or [])}

    def metric_label(m):
        name = m.get("name")
        display_name = name.title() if isinstance(name, str) else name
        unit = unit_map.get(m.get("unit_id"))
        if unit:
            return f"{display_name} ({unit})"
        return display_name

    metric_idx = st.selectbox("Metric", options=list(range(len(metrics))), format_func=lambda i: metric_label(metrics[i]))
    selected_metric = metrics[metric_idx]
    return selected_metric, unit_meta, unit_map
