import streamlit as st
import models
import utils
from st_keyup import st_keyup

@st.dialog("Confirm Metric Update")
def _confirm_metric_update_dialog(m, new_payload):
    """Summarizes changes and uses the centralized finalize_action for feedback."""
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
        utils.finalize_action(f"Updated: {new_payload['name'].title()}")

def show_edit_metrics(metrics_list, cats):
    """Focused Mobile Editor: Only shows the 'Active' metric for editing."""
    st.subheader("Edit Metric Details")
    
    # 1. Reuse the selector to pick which metric to edit (Sticky Logic)
    active_id = st.session_state.get("last_active_mid")
    selected_metric = select_metric(metrics_list, target_id=active_id)
    
    if not selected_metric:
        st.info("Select a metric above to edit its settings.")
        return

    # Update sticky state if user changes selection here
    st.session_state["last_active_mid"] = selected_metric['id']

    # 2. Render focused editor block
    cat_options = {c["id"]: c["name"].title() for c in (cats or [])}
    opt_ids = list(cat_options.keys())
    _render_metric_editor_block(selected_metric, opt_ids, cat_options)

def _render_metric_editor_block(m, opt_ids, cat_options):
    """Vertical-first editor block with integrated safety checks."""
    with st.container(border=True):
        new_name = st.text_input("Metric Name", value=m['name'], key=f"ed_nm_{m['id']}")
        
        col_unit, col_cat = st.columns(2)
        new_unit = col_unit.text_input("Unit", value=m.get('unit_name', ''), key=f"ed_un_{m['id']}")
        
        sorted_opt_ids = sorted(opt_ids, key=lambda x: cat_options.get(x, "").lower())
        select_opts = sorted_opt_ids + ["NEW_CAT"]
        
        new_cat_id = col_cat.selectbox(
            "Category", options=select_opts,
            format_func=lambda x: "✨ New..." if x == "NEW_CAT" else cat_options.get(x, "Uncat"),
            index=select_opts.index(m.get("category_id")) if m.get("category_id") in select_opts else 0,
            key=f"ed_ct_{m['id']}"
        )

        inline_cat_name = None
        if new_cat_id == "NEW_CAT":
            inline_cat_name = st.text_input("New Category Name", key=f"inline_cat_{m['id']}")

        new_start, new_end = m.get("range_start", 0), m.get("range_end", 10)
        range_error = False
        error_msg = ""
        
        if m.get("unit_type") == "integer_range":
            rcol1, rcol2 = st.columns(2)
            new_start = rcol1.number_input("Min", value=int(m.get("range_start", 0)), step=1, key=f"rs_{m['id']}")
            new_end = rcol2.number_input("Max", value=int(m.get("range_end", 10)), step=1, key=f"re_{m['id']}")
            
            if new_start >= new_end:
                range_error, error_msg = True, "Max must be strictly greater than Min."

            if not range_error:
                actual_min, actual_max = models.get_metric_value_bounds(m['id'])
                if actual_min is not None:
                    if new_start > actual_min:
                        range_error, error_msg = True, f"Existing data has values as low as {actual_min}."
                    elif new_end < actual_max:
                        range_error, error_msg = True, f"Existing data has values as high as {actual_max}."

        if range_error:
            st.error(error_msg)

        if st.button("💾 Save Changes", key=f"upd_sv_{m['id']}", type="primary", use_container_width=True, disabled=range_error):
            target_cat_id = utils.ensure_category_id(new_cat_id, inline_cat_name)
            
            payload = {
                "name": utils.normalize_name(new_name),
                "unit_name": utils.normalize_name(new_unit),
                "category_id": target_cat_id
            }
            if m.get("unit_type") == "integer_range":
                payload["range_start"], payload["range_end"] = new_start, new_end

            _confirm_metric_update_dialog(m, payload)

def show_create_metric(cats):
    """
    Mobile-optimized metric creation.
    Replaces the collapsed expander with a dedicated, focused layout.
    """
    st.subheader("Define New Metric")
    
    with st.container(border=True):
        # 1. Basic Metadata
        mn = st.text_input("Metric Name", placeholder="e.g., Daily Steps", key="create_mn")
        
        col_unit, col_type = st.columns(2)
        unit_name = col_unit.text_input("Unit", placeholder="e.g., km", key="create_unit")
        unit_type = col_type.selectbox(
            "Value Type", 
            options=["float", "integer", "integer_range"],
            key="create_utype"
        )

        # 2. Dynamic Range Configuration
        range_start, range_end = 0, 10
        range_error = False
        if unit_type == "integer_range":
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min Value", value=0, step=1, key="create_rs")
            range_end = rcol2.number_input("Max Value", value=10, step=1, key="create_re")
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
                    "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                    "unit_type": unit_type, 
                    "category_id": final_cat_id
                }
                
                if unit_type == "integer_range":
                    payload["range_start"] = range_start
                    payload["range_end"] = range_end

                models.create_metric(payload)
                
                # Centralized feedback and refresh
                utils.finalize_action(f"Created: {mn.strip().title()}")
            else:
                st.warning("Please enter a name for the metric.")

def on_metric_selected():
    """Syncs the internal widget state to the global sticky state."""
    if "metric_pill_selector" in st.session_state:
        st.session_state["last_active_mid"] = st.session_state["metric_pill_selector"]
        st.session_state["metric_search"] = ""

def select_metric(metrics, target_id=None):
    if not metrics:
        return None
    
    sorted_metrics = sorted(metrics, key=lambda x: x.get("name", "").lower())
    
    # 1. IDENTIFY ACTIVE METRIC FOR THE HEADER
    active_id = st.session_state.get("last_active_mid")
    selected_obj = next((m for m in sorted_metrics if str(m['id']) == str(active_id)), None)
    if not selected_obj:
        selected_obj = sorted_metrics[0]

    # 2. COLLAPSIBLE SELECTOR BOX
    # The label acts as a status indicator: "Current: Steps (km)"
    header_label = f"🎯 Tracking: {utils.format_metric_label(selected_obj)}"
    
    with st.expander(header_label, expanded=False):
        # 3. INSTANT SEARCH (st_keyup)
        search_query = st_keyup(
            "Filter metrics...",
            key="metric_search",
            value=st.session_state.get("metric_search", ""),
            placeholder="Type to find another...",
            label_visibility="collapsed"
        ).lower().strip()

        # 4. FILTERING LOGIC
        filtered_metrics = [
            m for m in sorted_metrics 
            if search_query in m.get("name", "").lower() or 
               search_query in m.get("unit_name", "").lower()
        ] if search_query else sorted_metrics

        # 5. RESULT PILLS
        pill_options = {m['id']: utils.format_metric_label(m) for m in filtered_metrics}
        
        if pill_options:
            st.segmented_control(
                "Change Metric",
                options=list(pill_options.keys()),
                format_func=lambda x: pill_options.get(x),
                key="metric_pill_selector",
                selection_mode="single",
                label_visibility="collapsed",
                on_change=on_metric_selected,
                default=target_id if target_id in pill_options else list(pill_options.keys())[0]
            )
        else:
            st.caption("No matching metrics found.")

    return selected_obj