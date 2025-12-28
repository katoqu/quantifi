import streamlit as st
import pandas as pd
import models
import utils

def show_manage_lookups():
    with st.expander("Manage categories and units", expanded=False):
        new_cat = st.text_input("New category")
        if st.button("Add category") and new_cat.strip():
            name_norm = utils.normalize_name(new_cat)
            existing = models.get_categories() or []
            if any(c["name"].lower() == name_norm for c in existing):
                st.info("Category already exists (case-insensitive)")
            else:
                models.create_category(name_norm)
                st.cache_data.clear() 
                st.success("Category added")
                st.rerun()

        new_unit = st.text_input("New unit")
        unit_type = st.selectbox("Unit type", ("float", "integer", "integer range"))
        range_start = None
        range_end = None
        if unit_type == "integer range":
            col1, col2 = st.columns(2)
            with col1:
                range_start = st.number_input("Range start", step=1)
            with col2:
                range_end = st.number_input("Range end", step=1)

        if st.button("Add unit") and new_unit.strip():
            name_norm = utils.normalize_name(new_unit)
            existing = models.get_units() or []
            if any(u["name"].lower() == name_norm for u in existing):
                st.info("Unit already exists (case-insensitive)")
            else:
                payload = {"name": name_norm, "unit_type": ("integer_range" if unit_type == "integer range" else unit_type)}
                if range_start is not None and range_end is not None:
                    payload["range_start"] = int(range_start)
                    payload["range_end"] = int(range_end)
                models.create_unit(payload)
                # --- ADD THIS LINE ---
                st.cache_data.clear() 
                st.success("Unit added")
                st.rerun()

        units_list = models.get_units() or []
        if units_list:
            rows = []
            for u in units_list:
                name = u.get("name", "").title()
                utype = u.get("unit_type", "float")
                if utype == "integer_range":
                    rs = u.get("range_start")
                    re = u.get("range_end")
                    range_str = f"{rs} - {re}" if rs is not None or re is not None else ""
                else:
                    range_str = ""
                rows.append({"name": name, "type": utype, "range": range_str})
            try:
                df_units = pd.DataFrame(rows)
                st.dataframe(df_units)
            except Exception:
                st.write(rows)

    cats = models.get_categories()
    units = models.get_units()
    return cats, units
