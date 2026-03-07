"""Create metric component."""

import streamlit as st
import models
import utils
from .metrics_dialogs import _METRIC_KIND_OPTIONS, _KIND_TO_UNIT_TYPE


def show_create_metric(cats):
    """
    Mobile-optimized metric creation.
    Replaces the collapsed expander with a dedicated, focused layout.
    """
    st.subheader("Define New Metric")
    
    with st.container(border=True):
        # 1. Basic Metadata
        mn = st.text_input("Metric Name", placeholder="e.g., Daily Steps", key="create_mn")

        # 1.5 Add Description Field
        desc = st.text_area("Description (Optional)", placeholder="What does this metric track?", key="create_desc")

        col_unit, col_kind = st.columns(2)
        unit_name = col_unit.text_input("Unit", placeholder="e.g., km", key="create_unit")
        
        def format_metric_kind(k: str) -> str:
            kind_labels = {"quantitative": "Quantitative", "count": "Count", "score": "Score"}
            return kind_labels.get(k, k)
        
        metric_kind = col_kind.selectbox(
            "Kind",
            options=_METRIC_KIND_OPTIONS,
            format_func=format_metric_kind,
            key="create_mkind",
        )
        unit_type = _KIND_TO_UNIT_TYPE[metric_kind]

        # 2. Dynamic Range Configuration
        range_start, range_end = 0, 10
        range_error = False
        higher_is_better = True
        if metric_kind == "score":
            higher_is_better = st.toggle("Higher is better", value=True, key="create_hib")
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min Value", value=1, step=1, key="create_rs")
            range_end = rcol2.number_input("Max Value", value=5, step=1, key="create_re")
            if range_start >= range_end:
                st.error("Max must be greater than Min")
                range_error = True

        # 3. Category Assignment
        sorted_cats = sorted(cats, key=lambda x: x["name"].lower()) if cats else []
        cat_opts = (
            [(None, "— none —")] + 
            [(c["id"], c["name"].title()) for c in sorted_cats] + 
            [("NEW_CAT", "✨ Create New...")]
        )
        
        cat_choice = st.selectbox(
            "Assign Category", 
            [o[0] for o in cat_opts], 
            format_func=lambda i: next((n for (_id, n) in cat_opts if _id == i), "— none —"),
            key="create_cat"
        )
        
        new_cat_name = None
        if cat_choice == "NEW_CAT":
            new_cat_name = st.text_input("New Category Name", key="create_new_cat_name")

        # 4. Vertical Primary Action
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Create Metric", type="primary", use_container_width=True, disabled=range_error):
            if mn.strip():
                final_cat_id = utils.ensure_category_id(cat_choice, new_cat_name)
                
                payload = {
                    "name": utils.normalize_name(mn), 
                    "description": desc.strip() if desc else None,
                    "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                    "unit_type": unit_type, 
                    "metric_kind": metric_kind,
                    "category_id": final_cat_id
                }
                
                if metric_kind == "score":
                    payload["range_start"] = range_start
                    payload["range_end"] = range_end
                    payload["higher_is_better"] = bool(higher_is_better)

                models.create_metric(payload)
                
                # Centralized feedback and refresh
                utils.finalize_action(f"Created: {mn.strip().title()}")
            else:
                st.warning("Please enter a name for the metric.")
