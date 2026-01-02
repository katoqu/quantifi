import streamlit as st
import models
import utils

import streamlit as st
import models
import utils

import streamlit as st
import models
import utils

def show_manage_lookups():
    """
    Ultra-compact, single-line category management.
    Optimized for maximum information density on mobile screens.
    """
    st.subheader("📁 Categories")
    cats = models.get_categories() or []
    
    # 1. Header with 'Add' Popover
    col_info, col_btn = st.columns([1, 1])
    with col_info:
        st.caption("Manage groups")
    with col_btn:
        with st.popover("➕ New", use_container_width=True):
            new_name = st.text_input("Name", key="new_cat_input")
            if st.button("Save", type="primary", use_container_width=True):
                if new_name.strip():
                    normalized = utils.normalize_name(new_name)
                    models.create_category(normalized)
                    # This triggers the toast and the rerun that closes the popover
                    utils.finalize_action(f"Created: {normalized.title()}")

    # 2. Filter Box
    cat_names = [c['name'].title() for c in cats]
    selected_search = st.selectbox(
        "Search",
        options=["— All —"] + sorted(cat_names),
        index=0,
        label_visibility="collapsed"
    )

    filtered = [
        c for c in cats 
        if selected_search == "— All —" or c['name'].lower() == selected_search.lower()
    ]

    if not filtered:
        st.info("No categories.")
        return

    metrics_list = models.get_metrics() or []

    # 3. Ultra-Compact List
    for cat in filtered:
        usage_count = sum(1 for m in metrics_list if m.get('category_id') == cat['id'])
        
        with st.container(border=True):
            c1, c2, c3 = st.columns([3, 1, 1])
            
            with c1:
                st.markdown(f"**{cat['name'].title()}** ({usage_count})")
            
            with c2:
                with st.popover("📝", use_container_width=True):
                    upd_val = st.text_input("Rename", value=cat['name'], key=f"ren_v_{cat['id']}")
                    if st.button("Update", key=f"upd_v_{cat['id']}", type="primary", use_container_width=True):
                        new_cat_name = utils.normalize_name(upd_val)
                        models.update_category(cat['id'], new_cat_name)
                        # finalize_action ensures the popover clears upon the subsequent rerun
                        utils.finalize_action(f"Renamed to: {new_cat_name.title()}")

            with c3:
                if usage_count == 0:
                    with st.popover("🗑️", use_container_width=True):
                        st.warning("Delete this category?")
                        if st.button("Confirm Delete", key=f"del_v_{cat['id']}", type="secondary", use_container_width=True):
                            models.delete_category(cat['id'])
                            # Use centralized finalize_action with a custom icon
                            utils.finalize_action(f"Deleted: {cat['name'].title()}", icon="🗑️")
                else:
                    st.button("🔒", help="In use by metrics", disabled=True, use_container_width=True, key=f"lck_v_{cat['id']}")