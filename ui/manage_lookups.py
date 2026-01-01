import streamlit as st
import pandas as pd
import models
import utils

def show_manage_lookups():
    """
    Simplified to handle only categories. Units are now defined 
    directly within each metric.
    """
    with st.expander("Manage categories", expanded=False):
        new_cat = st.text_input("New category name")
        if st.button("Add category") and new_cat.strip():
            name_norm = utils.normalize_name(new_cat)
            existing = models.get_categories() or []
            if any(c["name"].lower() == name_norm for c in existing):
                st.info("Category already exists.")
            else:
                models.create_category(name_norm)
                st.cache_data.clear() 
                st.success("Category added")
                st.rerun()

        # Display current categories
        cats_list = models.get_categories() or []
        if cats_list:
            df_cats = pd.DataFrame([{"Name": c["name"].title()} for c in cats_list])
            st.table(df_cats)

    return cats_list