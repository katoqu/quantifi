import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page, changes
from ui import admin_page as admin_page_ui

def tracker_page():
    """Main dashboard controller optimized for mobile."""
    # --- 1. PRE-RENDER NAVIGATION LOGIC ---
    # Catch pill selection BEFORE rendering the segmented control
    back_pill_key = "pnav_Tracker_Overview"
    if st.session_state.get(back_pill_key) is not None:
        st.session_state[back_pill_key] = None
        st.session_state["tracker_view_selector"] = "Overview"

    # Handle deep link triggers
    if st.session_state.get("nav_to_record_trigger"):
        st.session_state["tracker_view_selector"] = "Record"
        st.session_state["nav_to_record_trigger"] = False 

    # --- 2. DATA LOADING & STATE ---
    all_metrics = models.get_metrics(include_archived=True) or []

    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"
    if "last_active_mid" not in st.session_state:
        st.session_state["last_active_mid"] = None

    utils.apply_custom_tabs_css()

    # --- 4. NAVIGATION HEADER ---
    st.header('Quantif👁')
    view_options = ["Overview", "Record", "Changes", "Analytics", "Edit"]
    st.segmented_control(
            "Navigation", 
            options=view_options, 
            selection_mode="single",
            label_visibility="collapsed",
            key="tracker_view_selector" 
        )
    
    view_mode = st.session_state["tracker_view_selector"]
    last_view = st.session_state.get("last_tracker_view_selection")
    if last_view != view_mode and view_mode in ("Record", "Analytics", "Edit"):
        st.session_state["metric_selector_open"] = False
        st.session_state["metric_selector_reset_token"] = (
            st.session_state.get("metric_selector_reset_token", 0) + 1
        ) % 5
    st.session_state["last_tracker_view_selection"] = view_mode

        # Back Button Pill (simplified label)
    if view_mode != "Overview":
        utils.render_back_button(target_page_title="Tracker", target_tab="Overview")

#    st.html('<div style="height: 15px;"></div>')

    # --- 5. METRIC SELECTION (Only for sub-views) ---

    selected_metric = None
    if view_mode not in ("Overview", "Changes"):
        active_id = st.session_state.get("last_active_mid")
        selected_metric = metrics.select_metric(all_metrics, target_id=active_id)
        
        if selected_metric:
            st.session_state["last_active_mid"] = selected_metric['id']

    # --- 6. CONTENT ROUTING ---
    if view_mode == "Overview":
        all_entries = models.get_all_entries_bulk()
        landing_page.show_landing_page(all_metrics, all_entries)
        
    elif view_mode == "Record" and selected_metric:
        capture.show_tracker_suite(selected_metric)

    elif view_mode == "Changes":
        changes.show_changes()

    elif view_mode == "Analytics" and selected_metric:
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
    back_pill_key = "pnav_Tracker_Overview"
    if st.session_state.get(back_pill_key) is not None:
        st.session_state[back_pill_key] = None
        st.session_state["tracker_view_selector"] = "Overview"
        
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
        utils.render_back_button(target_page_title="Tracker", target_tab="Overview")
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
