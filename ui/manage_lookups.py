import streamlit as st
import pandas as pd
import models
import utils

def show_manage_lookups():
    st.subheader("Manage Categories")
    cats = models.get_categories() or []
    
    # 1. Existing Categories with Edit option
    for cat in cats:
        col1, col2 = st.columns([3, 1])
        col1.write(f"**{cat['name'].title()}**")
        
        with col2.popover("Edit"):
            new_name = st.text_input("New Name", value=cat['name'], key=f"edit_cat_{cat['id']}")
            if st.button("Save", key=f"btn_cat_{cat['id']}"):
                models.update_category(cat['id'], utils.normalize_name(new_name))
                st.cache_data.clear() # Clear cache so changes show everywhere
                st.rerun()

    # 2. Add New Category
    new_cat = st.text_input("New category name")
    if st.button("Add category") and new_cat.strip():
        name_norm = utils.normalize_name(new_cat)
        if any(c["name"].lower() == name_norm for c in cats):
            st.info("Category already exists.")
        else:
            models.create_category(name_norm)
            st.cache_data.clear() 
            st.rerun()