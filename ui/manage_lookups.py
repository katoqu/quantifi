import streamlit as st
import models
import utils

def show_manage_lookups():
    """
    Refactored Category Management: Uses the sticky 'Focus' pattern 
    to match the Metric Editor layout.
    """
    st.subheader("Manage Categories")
    
    # 1. Fetch Categories
    cats = models.get_categories() or []
    if not cats:
        st.info("No categories found. Use the 'New' button to create one.")
        return

    # 2. Search & Select (Sticky Pattern)
    # We store the selected category ID in session state to keep it 'sticky'
    if "last_active_cat_id" not in st.session_state:
        st.session_state["last_active_cat_id"] = None

    cat_options = {c['id']: c['name'].title() for c in cats}
    sorted_cat_ids = sorted(cat_options.keys(), key=lambda x: cat_options[x].lower())
    
    # Calculate index for stickiness
    default_index = 0
    active_id = st.session_state["last_active_cat_id"]
    if active_id and active_id in sorted_cat_ids:
        default_index = sorted_cat_ids.index(active_id)

    selected_cat_id = st.selectbox(
        "🔍 Search or Select Category",
        options=sorted_cat_ids,
        format_func=lambda x: cat_options[x],
        index=default_index,
        key="cat_search_selector"
    )
    
    # Update global stickiness
    st.session_state["last_active_cat_id"] = selected_cat_id
    
    # 3. The Focused Editor Block
    # Fetch details for the focused category
    target_cat = next((c for c in cats if c['id'] == selected_cat_id), None)
    
    if target_cat:
        metrics_list = models.get_metrics() or []
        usage_count = sum(1 for m in metrics_list if m.get('category_id') == target_cat['id'])
        
        _render_category_editor_block(target_cat, usage_count)

@st.fragment
def _render_category_editor_block(cat, usage_count):
    """Vertical focused editor matching the Metric editor style."""
    with st.container(border=True):
        st.caption(f"Editing Category (Used by {usage_count} metrics)")
        
        # Action: Rename
        upd_val = st.text_input("Category Name", value=cat['name'].title(), key=f"cat_nm_{cat['id']}")
        
        if st.button("💾 Save Changes", type="primary", use_container_width=True):
            new_name = utils.normalize_name(upd_val)
            models.update_category(cat['id'], new_name)
            utils.finalize_action(f"Renamed to: {new_name.title()}")

        # Action: Delete (Only if unused)
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
        if usage_count == 0:
            if st.button("🗑️ Delete Category", type="secondary", use_container_width=True):
                models.delete_category(cat['id'])
                utils.finalize_action(f"Deleted: {cat['name'].title()}", icon="🗑️")
        else:
            st.button("🔒 Locked (In Use)", disabled=True, use_container_width=True, 
                      help="Categories used by metrics cannot be deleted.")