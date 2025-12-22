import streamlit as st
import models
import utils

# 1. Define Dialogs
@st.dialog("Create New Category")
def category_creation_dialog():
    new_cat = st.text_input("Category Name")
    if st.button("Create Category"):
        if new_cat.strip():
            name_norm = utils.normalize_name(new_cat)
            existing = models.get_categories() or []
            if any(c["name"].lower() == name_norm for c in existing):
                st.error("Category already exists")
            else:
                models.create_category(name_norm)
                # Auto-select the newly created category
                updated = models.get_categories() or []
                new_obj = next((c for c in updated if c.get("name") == name_norm), None)
                if new_obj:
                    st.session_state["dc_metric_cat"] = new_obj.get("id")
                st.rerun()

@st.dialog("Create New Unit")
def unit_creation_dialog():
    new_unit_name = st.text_input("New unit name")
    unit_type = st.selectbox("Unit type", ("float", "integer", "integer range"))
    
    range_start = None
    range_end = None
    if unit_type == "integer range":
        col1, col2 = st.columns(2)
        with col1:
            range_start = st.number_input("Range start", step=1)
        with col2:
            range_end = st.number_input("Range end", step=1)

    if st.button("Submit"):
        if new_unit_name:
            name_norm = utils.normalize_name(new_unit_name)
            existing = models.get_units() or []
            if any(u["name"].lower() == name_norm for u in existing):
                st.error("Unit already exists (case-insensitive)")
            else:
                payload = {
                    "name": name_norm, 
                    "unit_type": ("integer_range" if unit_type == "integer range" else unit_type)
                }
                if unit_type == "integer range":
                    payload["range_start"] = int(range_start)
                    payload["range_end"] = int(range_end)
                
                models.create_unit(payload)
                
                units_updated = models.get_units() or []
                new_unit = next((u for u in units_updated if u.get("name") == name_norm), None)
                if new_unit:
                    st.session_state["dc_unit_select"] = new_unit.get("id")
                st.rerun()

def show_define_and_configure():
    st.header("Configurations")
    
    # --- Metric Creation ---
    with st.expander("Metrics", expanded=False):
        mn = st.text_input("Metric name", key="dc_metric_name")
        
        # Category Selection Row
        st.markdown("**Category**")
        cats = models.get_categories() or []
        cat_options = [None] + [c["id"] for c in cats]
        
        def _format_cat(i):
            if i is None: return "— none —"
            cat = next((c for c in cats if c.get("id") == i), None)
            return cat.get("name", "").title() if cat else "— none —"

        col_cat_sel, col_cat_btn = st.columns([3, 1])
        with col_cat_sel:
            cat_choice = st.selectbox(
                "Choose category", 
                cat_options, 
                format_func=_format_cat, 
                key="dc_metric_cat"
            )
        with col_cat_btn:
            st.write("⠀") # Spacer
            if st.button("➕ New Category", key="btn_new_cat"):
                category_creation_dialog()

        # Unit Selection Row
        st.markdown("**Unit**")
        units = models.get_units() or []
        unit_ids = [None] + [u.get("id") for u in units]
        
        def _format_unit(i):
            if i is None: return "— none —"
            unit = next((u for u in units if u.get("id") == i), None)
            return unit.get("name", "").title() if unit else "— none —"

        col_unit_sel, col_unit_btn = st.columns([3, 1])
        with col_unit_sel:
            unit_choice_existing = st.selectbox(
                "Choose unit", 
                unit_ids, 
                format_func=_format_unit, 
                key="dc_unit_select"
            )
        with col_unit_btn:
            st.write("⠀") # Spacer
            if st.button("➕ New Unit", key="btn_new_unit"):
                unit_creation_dialog()

        st.divider()

        if st.button("Create metric", key="dc_create_metric", type="primary", use_container_width=True):
            if mn.strip():
                name_norm = utils.normalize_name(mn)
                if any(m.get("name", "").lower() == name_norm for m in (models.get_metrics() or [])):
                    st.error("Metric already exists")
                else:
                    payload = {"name": name_norm}
                    if cat_choice: payload["category_id"] = cat_choice
                    if unit_choice_existing: payload["unit_id"] = unit_choice_existing
                    models.create_metric(payload)
                    st.success(f"Metric '{mn}' created!")
            else:
                st.error("Please enter a metric name.")

    return models.get_categories() or [], models.get_units() or []