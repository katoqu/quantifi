import streamlit as st
import models
import utils

def show_manage_lookups():
    """
    Refactored Category Management: Uses the sticky 'Focus' pattern 
    to match the Metric Editor layout.
    """
    st.subheader("Manage Categories")
    
    # 0. Create New Category (always available)
    with st.container(border=True):
        st.caption("Create New Category")
        with st.form("manage_create_category", clear_on_submit=True):
            new_cat_name = st.text_input(
                "New Category Name",
                key="manage_new_cat_name"
            )
            existing_notice = st.session_state.get("manage_cat_notice")
            notice_name = st.session_state.get("manage_cat_notice_name")
            norm_input = utils.normalize_name(new_cat_name) if new_cat_name else ""
            if existing_notice and (not norm_input or (notice_name and norm_input != notice_name)):
                st.session_state["manage_cat_notice"] = None
                st.session_state["manage_cat_notice_name"] = None
                existing_notice = None
            if existing_notice:
                st.info(existing_notice)
            submitted = st.form_submit_button("✨ Create Category", use_container_width=True)
        if submitted:
            norm_name = utils.normalize_name(new_cat_name)
            if not norm_name:
                st.warning("Please enter a category name.")
            else:
                existing = models.get_category_by_name(norm_name)
                if existing:
                    st.session_state["manage_cat_notice"] = (
                        f"Category already exists: {existing['name'].title()}"
                    )
                    st.session_state["manage_cat_notice_name"] = norm_name
                    st.session_state["last_active_cat_id"] = existing["id"]
                    st.rerun()
                else:
                    models.create_category(norm_name)
                    created = models.get_category_by_name(norm_name)
                    if created:
                        st.session_state["last_active_cat_id"] = created["id"]
                    st.session_state["manage_cat_notice"] = None
                    st.session_state["manage_cat_notice_name"] = None
                    utils.finalize_action(f"Created: {norm_name.title()}")
                    st.rerun()

    # 1. Fetch Categories
    cats = models.get_categories() or []
    if not cats:
        st.info("No categories found. Use the 'New' button to create one.")
        return
        
    _render_category_editor_block(cats)

@st.fragment
def _render_category_editor_block(cats):
    """Vertical focused editor matching the Metric editor style."""
    # Sticky state for selection and edit mode
    if "last_active_cat_id" not in st.session_state:
        st.session_state["last_active_cat_id"] = None
    if "cat_edit_mode" not in st.session_state:
        st.session_state["cat_edit_mode"] = False

    cat_options = {c['id']: c['name'].title() for c in cats}
    sorted_cat_ids = sorted(cat_options.keys(), key=lambda x: cat_options[x].lower())

    active_id = st.session_state["last_active_cat_id"]
    if not active_id or active_id not in sorted_cat_ids:
        active_id = sorted_cat_ids[0]

    with st.container(border=True):
        st.caption("Edit Category")

        if not st.session_state["cat_edit_mode"]:
            selected_cat_id = st.selectbox(
                "Select Category",
                options=sorted_cat_ids,
                format_func=lambda x: cat_options[x],
                index=sorted_cat_ids.index(active_id),
                key="cat_search_selector"
            )
            st.session_state["last_active_cat_id"] = selected_cat_id
        else:
            selected_cat_id = st.session_state["last_active_cat_id"]

        target_cat = next((c for c in cats if c['id'] == selected_cat_id), None)
        if not target_cat:
            return

        usage_count = models.get_category_usage_count(target_cat["id"])

#        st.caption(f"Editing Category (Used by {usage_count} metrics)")

        if not st.session_state["cat_edit_mode"]:
            if st.button("✏️ Rename", use_container_width=True):
                st.session_state["cat_edit_mode"] = True
                st.session_state["cat_edit_name"] = target_cat["name"].title()
                st.rerun()
        else:
            if "cat_edit_name" not in st.session_state:
                st.session_state["cat_edit_name"] = target_cat["name"].title()
            upd_val = st.text_input(
                "Insert New Name",
                key="cat_edit_name"
            )
            col_save, col_cancel = st.columns(2)
            if col_save.button("💾 Save Changes", type="primary", use_container_width=True):
                new_name = utils.normalize_name(upd_val)
                models.update_category(target_cat['id'], new_name)
                utils.finalize_action(f"Renamed to: {new_name.title()}")
                st.session_state["cat_edit_mode"] = False
                st.session_state.pop("cat_edit_name", None)
                st.rerun()
            if col_cancel.button("Cancel", use_container_width=True):
                st.session_state["cat_edit_mode"] = False
                st.session_state.pop("cat_edit_name", None)
                st.rerun()
        # Action: Delete (Only if unused)
        if not st.session_state["cat_edit_mode"]:
            st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
            if usage_count == 0:
                if st.button("🗑️ Delete Category", type="secondary", use_container_width=True):
                    models.delete_category(target_cat['id'])
                    utils.finalize_action(f"Deleted: {target_cat['name'].title()}", icon="🗑️")
                    st.session_state["last_active_cat_id"] = None
                    st.session_state["cat_edit_mode"] = False
                    st.rerun()
            else:
                st.button(
                    "🔒 Locked (In Use)",
                    disabled=True,
                    use_container_width=True,
                    help="Categories used by metrics cannot be deleted."
                )
