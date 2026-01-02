import streamlit as st
import models
import utils

def show_manage_lookups():
    """
    Renders a category management interface with type-ahead selection
    and card-based editing.
    """
    st.subheader("📁 Category Management")
    cats = models.get_categories() or []
    
    # 1. Header with 'Add' Popover
    col_info, col_btn = st.columns([2, 1])
    col_info.write("Organize your metrics into logical groups.")
    with col_btn.popover("➕ Create Category", use_container_width=True):
        new_name = st.text_input("Category Name", key="new_cat_input")
        if st.button("Save New Category", type="primary", use_container_width=True):
            if new_name.strip():
                models.create_category(utils.normalize_name(new_name))
                st.cache_data.clear()
                st.rerun()

    st.divider()

    # 2. Type-ahead Selection Box
    cat_names = [c['name'].title() for c in cats]
    selected_search = st.selectbox(
        "🔍 Search and Focus Category",
        options=["— Show All —"] + sorted(cat_names),
        index=0,
        help="Start typing to find a specific category."
    )

    # 3. Filtering Logic
    filtered = [
        c for c in cats 
        if selected_search == "— Show All —" or c['name'].lower() == selected_search.lower()
    ]

    if not filtered:
        st.info("No categories found.")
        return

    metrics_list = models.get_metrics() or []

    # 4. Category Card List
    for cat in filtered:
        with st.container(border=True):
            c_info, c_edit, c_status = st.columns([3, 1, 1])
            
            with c_info:
                usage_count = sum(1 for m in metrics_list if m.get('category_id') == cat['id'])
                st.markdown(f"### {cat['name'].title()}")
                st.caption(f"Linked to **{usage_count}** metrics.")

            with c_edit:
                st.write("") # Alignment spacer
                with st.popover("📝 Rename", use_container_width=True):
                    upd_val = st.text_input("New Name", value=cat['name'], key=f"ren_input_{cat['id']}")
                    if st.button("Update", key=f"upd_btn_{cat['id']}", type="primary", use_container_width=True):
                        models.update_category(cat['id'], utils.normalize_name(upd_val))
                        st.cache_data.clear()
                        st.rerun()

            with c_status:
                st.write("") # Alignment spacer
                if usage_count == 0:
                    with st.popover("🗑️", use_container_width=True):
                        st.error("Delete this category?")
                        if st.button("Confirm Delete", key=f"del_cat_{cat['id']}", type="secondary", use_container_width=True):
                            models.delete_category(cat['id']) # Ensure this exists in models.py
                            st.cache_data.clear()
                            st.rerun()
                else:
                    # FIXED: Added unique key to prevent StreamlitDuplicateElementId
                    st.button(
                        "🔒", 
                        help="Category is currently in use by metrics and cannot be deleted.", 
                        disabled=True, 
                        use_container_width=True,
                        key=f"lock_btn_{cat['id']}" 
                    )