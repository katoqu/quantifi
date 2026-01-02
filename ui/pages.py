import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor, importer, landing_page

import streamlit as st
import models
import utils
from ui import landing_page, metrics, capture

def apply_custom_tabs_css():
    """
    Ultra-robust CSS for segmented tabs.
    Targets the specific Streamlit radio button structure to ensure 
    active state highlighting is visible.
    """
    st.markdown("""
        <style>
        /* 1. Main Container */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            background-color: #f0f2f6;
            padding: 5px;
            border-radius: 12px;
            border: 1px solid #e0e0e0;
            width: fit-content;
            margin-bottom: 20px;
        }

        /* 2. Hide the radio circle input */
        div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]) {
            display: none !important;
        }

        /* 3. Base Label (Inactive Tab) */
        div[data-testid="stRadio"] label {
            background-color: transparent !important;
            padding: 8px 25px !important;
            border-radius: 9px !important;
            margin: 0px 3px !important;
            cursor: pointer !important;
            border: none !important;
            transition: all 0.2s ease;
            font-weight: 500;
            color: #555 !important;
        }

        /* 4. Active Tab Highlighting */
        /* This looks for the label that contains the 'checked' input */
        div[data-testid="stRadio"] label:has(input:checked) {
            background-color: white !important;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.1) !important;
        }
        
        /* Forces the text color/style for the active label */
        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #FF4B4B !important;
            font-weight: 700 !important;
        }

        /* Reset p-tag margins for vertical centering */
        div[data-testid="stRadio"] label p {
            margin: 0px !important;
            font-size: 16px;
        }
        </style>
    """, unsafe_allow_html=True)

def tracker_page():
    """
    Main dashboard controller. 
    Uses Session State as the single source of truth to avoid 'Duplicate Value' errors.
    """
    all_metrics = models.get_metrics() or []
    
    if not all_metrics:
        st.title("QuantifI")
        st.info("👋 Welcome! Go to Settings to create your first tracking target.")
        return

    # Apply the visual theme
    apply_custom_tabs_css()

    # --- 1. STATE INITIALIZATION ---
    # We must ensure the key exists in session_state BEFORE the widget is created
    if "tracker_view_selector" not in st.session_state:
        st.session_state["tracker_view_selector"] = "Overview"

    # --- 2. HANDLE DEEP LINK TRIGGER ---
    requested_mid = st.query_params.get("metric_id")
    if requested_mid:
        # Force the widget state via the Session State API
        st.session_state["tracker_view_selector"] = "Record Data"
        st.session_state["requested_metric_id"] = requested_mid
        # Clear params to keep the URL clean
        st.query_params.clear()

    # --- 3. RENDER NAVIGATION (The Segmented Tabs) ---
    # FIX: We remove the 'index' parameter entirely. 
    # Streamlit will automatically use st.session_state["tracker_view_selector"]
    view_options = ["Overview", "Record Data"]
    
    st.radio(
        "Navigation", 
        view_options, 
        horizontal=True, 
        label_visibility="collapsed",
        key="tracker_view_selector" 
    )
    
    # Extract current view from the widget's state
    view_mode = st.session_state["tracker_view_selector"]
    st.divider()

    # --- 4. ROUTING LOGIC ---
    if view_mode == "Overview":
        if "requested_metric_id" in st.session_state:
            del st.session_state["requested_metric_id"]
        landing_page.show_landing_page()
        
    else:
        # --- RECORD DATA VIEW ---
        active_mid = st.session_state.get("requested_metric_id")
        
        default_idx = 0
        if active_mid:
            for idx, m in enumerate(all_metrics):
                if m['id'] == active_mid:
                    default_idx = idx
                    break

        selected_metric = metrics.select_metric(all_metrics, index=default_idx)
        
        if selected_metric:
            # Update the requested ID so selection persists
            st.session_state["requested_metric_id"] = selected_metric['id']
            capture.show_tracker_suite(selected_metric)

def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Please create metrics in Settings before editing data.")
        return

    selected_metric = metrics.select_metric(metrics_list)
    
    if selected_metric:
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """Refactored Settings page using Tabs for a cleaner UX."""
    st.title("Settings & Maintenance")
    
    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    last_ts = models.get_last_backup_timestamp()

    tab_metrics, tab_cats, tab_life = st.tabs([
        "📊 Manage Metrics", 
        "📁 Categories", 
        "💾 Data Lifecycle"
    ])

    with tab_metrics:
        if metrics_list:
            metrics.show_edit_metrics(metrics_list, cats)
            st.divider()
        metrics.show_create_metric(cats)

    with tab_cats:
        manage_lookups.show_manage_lookups()

    with tab_life:
        st.caption(f"🛡️ Last local backup: **{last_ts}**")
        importer.show_data_lifecycle_management()