import streamlit as st
import pandas as pd
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page, changes
from ui import admin_page as admin_page_ui


def _recent_metric_ids(all_entries, limit=5):
    """Return metric IDs with the most recent numeric entries."""
    if not all_entries:
        return []
    df = pd.DataFrame(all_entries)
    if df.empty or "recorded_at" not in df.columns:
        return []
    df["recorded_at"] = pd.to_datetime(df["recorded_at"], format="mixed", utc=True)
    value_series = df["value"] if "value" in df.columns else pd.Series(index=df.index, dtype="object")
    df["_value_num"] = pd.to_numeric(value_series, errors="coerce")
    measured_df = df[pd.notna(df["_value_num"])].copy()
    if measured_df.empty:
        return []
    latest_by_metric = measured_df.groupby("metric_id")["recorded_at"].max()
    recent_ids = list(latest_by_metric.sort_values(ascending=False).head(int(limit)).index)
    return recent_ids


def _filter_metrics_for_subview(all_metrics, cat_map, current_filter, *, recent_ids=None):
    if not current_filter:
        return list(all_metrics)
    if current_filter == "Recent":
        if not recent_ids:
            return []
        id_map = {str(m.get("id")): m for m in all_metrics}
        ordered = []
        for mid in recent_ids:
            m = id_map.get(str(mid))
            if m:
                ordered.append(m)
        return ordered
    return [m for m in all_metrics if cat_map.get(m.get("category_id")) == current_filter]

def tracker_page():
    """Main dashboard controller optimized for mobile."""
    # --- 1. PRE-RENDER NAVIGATION LOGIC ---
    # Catch pill selection BEFORE rendering the segmented control
    back_pill_key = "pnav_Tracker_Home"
    if st.session_state.get(back_pill_key) is not None:
        st.session_state[back_pill_key] = None
        st.session_state["tracker_view_selector"] = "Home"

    # Handle deep link triggers
    if st.session_state.get("nav_to_record_trigger"):
        st.session_state["tracker_view_selector"] = "Add"
        st.session_state["nav_to_record_trigger"] = False 

    # --- 2. DATA LOADING & STATE ---
    all_metrics = models.get_metrics(include_archived=True) or []
    active_metrics = [m for m in all_metrics if not m.get("is_archived", False)]

    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Home"
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    utils.apply_custom_tabs_css()

    # --- 4. NAVIGATION HEADER ---
    st.header('Quantif👁')
    view_options = ["Home", "Add", "Log", "Stats", "Edit"]
    if st.session_state.get("tracker_view_selector") not in view_options:
        st.session_state["tracker_view_selector"] = "Home"
    st.segmented_control(
            "Navigation", 
            options=view_options, 
            selection_mode="single",
            label_visibility="collapsed",
            key="tracker_view_selector" 
        )
    
    view_mode = st.session_state["tracker_view_selector"]
    last_view = st.session_state.get("last_tracker_view_selection")
    if last_view != view_mode and view_mode in ("Add", "Stats", "Edit"):
        st.session_state["metric_selector_open"] = False
        st.session_state["metric_selector_reset_token"] = (
            st.session_state.get("metric_selector_reset_token", 0) + 1
        ) % 5
    st.session_state["last_tracker_view_selection"] = view_mode

    # --- 4b. SUBVIEW FILTER PILLS (Add/Stats/Edit) ---
    filtered_metrics = active_metrics
    if view_mode in ("Add", "Stats", "Edit"):
        cats = models.get_categories() or []
        cat_map = {c["id"]: c["name"].title() for c in cats}
        cat_options = ["Recent"] + sorted([c["name"].title() for c in cats])

        filter_key = "tracker_subview_cat_filter"
        if st.session_state.get(filter_key) is not None and st.session_state.get(filter_key) not in cat_options:
            st.session_state[filter_key] = None

        st.pills(
            "Filter",
            options=cat_options,
            key=filter_key,
            label_visibility="collapsed",
            selection_mode="single",
        )

        current_filter = st.session_state.get(filter_key)
        recent_ids = None
        if current_filter == "Recent":
            recent_ids = _recent_metric_ids(models.get_all_entries_bulk(), limit=5)
        filtered_metrics = _filter_metrics_for_subview(
            active_metrics, cat_map, current_filter, recent_ids=recent_ids
        )

        # Back Button Pill (simplified label)
    if view_mode in ("Add", "Stats", "Edit"):
        utils.render_back_button(target_page_title="Tracker", target_tab="Home")

#    st.html('<div style="height: 15px;"></div>')

    # --- 5. METRIC SELECTION (Only for sub-views) ---

    selected_metric = None
    if view_mode not in ("Home", "Log"):
        if not filtered_metrics:
            st.info("No metrics match this filter.")
        else:
            active_id = st.session_state.get("last_active_mid")
            selected_metric = metrics.select_metric_dropdown(filtered_metrics, target_id=active_id)

    # --- 6. CONTENT ROUTING ---
    if view_mode == "Home":
        all_entries = models.get_all_entries_bulk()
        landing_page.show_landing_page(all_metrics, all_entries)
        
    elif view_mode == "Add" and selected_metric:
        capture.show_tracker_suite(selected_metric)

    elif view_mode == "Log":
        changes.show_changes()

    elif view_mode == "Stats" and selected_metric:
        landing_page.show_advanced_analytics_view(selected_metric)

    elif view_mode == "Edit" and selected_metric:
        data_editor.show_data_management_suite(selected_metric)
        
def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Edit")
    
    # 1. Fetch metrics
    metrics_list = models.get_metrics(include_archived=True) or []
    if not metrics_list:
        st.info("No metrics found. Please create metrics in Settings before editing data.")
        return

    # 2. SMART DEFAULT: Link to the shared global active metric key
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    # 3. Use the shared 'sticky' ID
    active_id = st.session_state["last_active_mid"]
    selected_metric = metrics.select_metric(metrics_list, target_id=active_id)
    
    if selected_metric:
        # 4. Update the shared state so it sticks if changed here too
        st.session_state["last_active_mid"] = selected_metric['id']
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """Refactored Settings with Sticky Header and Back Navigation."""
    # --- 1. PRE-RENDER NAVIGATION LOGIC ---
    back_pill_key = "pnav_Tracker_Home"
    if st.session_state.get(back_pill_key) is not None:
        st.session_state[back_pill_key] = None
        st.session_state["tracker_view_selector"] = "Home"
        
        # Switch back to Tracker page
        nav_pages = st.session_state.get("nav_pages", [])
        target_page = next((p for p in nav_pages if p.title == "Tracker"), None)
        if target_page:
            st.switch_page(target_page)

    st.header("Settings")
    
    if "config_tab_selection" not in st.session_state:
        st.session_state["config_tab_selection"] = "📊 Edit Metric"

    utils.apply_custom_tabs_css()

    # --- 3. STICKY HEADER CONTAINER ---
    with st.container():
        tab_options = ["📊 Edit Metric", "✨ New Metric", "📁 Categories", "⚙️ Ex/Import"]
        selected_tab = st.segmented_control(
            "Settings Menu",
            options=tab_options,
            selection_mode="single",
            label_visibility="collapsed",
            key="config_tab_selection"
        )

        last_tab = st.session_state.get("last_config_tab_selection")
        if last_tab != selected_tab and selected_tab == "📊 Edit Metric":
            st.session_state["metric_selector_open"] = False
            st.session_state["metric_selector_reset_token"] = (
                st.session_state.get("metric_selector_reset_token", 0) + 1
            ) % 5
        st.session_state["last_config_tab_selection"] = selected_tab
        
        # Simple Back Button
        utils.render_back_button(target_page_title="Tracker", target_tab="Home")
        st.html('<div style="height: 10px;"></div>')

    # --- 4. DATA LOADING & CONTENT ROUTING ---
    cats = models.get_categories() or []
    metrics_list = models.get_metrics(include_archived=True) or []
    
    if selected_tab == "📊 Edit Metric":    
        metrics.show_edit_metrics(metrics_list, cats)
    elif selected_tab == "✨ New Metric":
        metrics.show_create_metric(cats)
    elif selected_tab == "📁 Categories":
        manage_lookups.show_manage_lookups()
    elif selected_tab == "⚙️ Ex/Import":
        last_ts = models.get_last_backup_timestamp()
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()

def admin_page():
    admin_page_ui.render_admin_page()
