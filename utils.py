import pandas as pd
import models
import datetime as dt
import streamlit as st
import time


def normalize_name(name: str):
    """Standardizes names for database storage."""
    return name.strip().lower()

def ensure_category_id(choice, new_name_input):
    """
    Centralized logic to handle 'Create New' selections.
    Returns the selected ID or the newly created ID.
    """
    if choice == "NEW_CAT" and new_name_input:
        norm_cat = normalize_name(new_name_input)
        
        # Check if it exists first to avoid duplicates
        existing = models.get_category_by_name(norm_cat)
        if existing:
            return existing['id']
            
        models.create_category(norm_cat)
        new_cat_obj = models.get_category_by_name(norm_cat)
        return new_cat_obj['id'] if new_cat_obj else None
    
    return choice if choice != "NEW_CAT" else None

def format_metric_label(metric, unit_map=None):
    """Pulls unit_name directly from the metric object."""
    name = metric.get("name", "").title()
    unit = metric.get("unit_name", "").title()
    return f"{name} ({unit})" if unit else name

def collect_data(selected_metric, unit_meta=None):
    mid = selected_metric.get("id")
    m_name = selected_metric.get("name", "Metric").title() #
    m_unit = selected_metric.get("unit_name", "") #

    entries = models.get_entries(metric_id=mid) #
    if not entries:
        return pd.DataFrame(), m_unit, m_name #
        
    dfe = pd.DataFrame(entries) #
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"], format='ISO8601', utc=True) #
    
    # DEFAULT: Always provide data sorted by time for immediate visual feedback
    return dfe.sort_values("recorded_at", ascending=False), m_unit, m_name #

def to_datetz(date_obj):
    """Converts a date object to a datetime with a midday timestamp."""
    return dt.datetime.combine(date_obj, dt.time(12, 0))

def apply_custom_tabs_css():
    """
    Modern Native Mobile Layout:
    1. Pins the navigation header (Tabs, Back, Divider) to the top.
    2. Tightens all vertical gaps for a high-density 'app' feel.
    3. Styles the Back button as a clean, native-style text link.
    """
    st.markdown("""
        <style>
        /* --- 1. THE NAVIGATION TABS (Segmented Control) --- */
        div[data-testid="stSegmentedControl"] {
            display: flex !important;
            background-color: var(--secondary-background-color) !important;
            padding: 8px !important;
            border-radius: 16px !important;
            border: 1px solid var(--border-color) !important;
            margin: 0 auto 12px auto !important;
            width: 100% !important;
            max-width: 500px !important;
        }

        div[data-testid="stSegmentedControl"] button {
            flex: 1 !important;
            background-color: transparent !important;
            border-radius: 12px !important;
            border: none !important;
            color: var(--text-color) !important;
            opacity: 0.7;
            transition: all 0.15s ease-in-out !important;
        }

        div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
            background-color: var(--background-color) !important;
            box-shadow: 0px 3px 8px rgba(0,0,0,0.12) !important;
            opacity: 1 !important;
            color: #FF4B4B !important; 
            font-weight: 800 !important;
        }

        /* --- 2. THE STICKY NAVIGATION HEADER (Tabs + Back + Divider) --- */
        /* Targets the container wrapper to pin it to the top during scroll */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(button[key^="back_btn_"]) {
            position: sticky !important;
            top: 2.85rem !important; /* Offset for Streamlit top bar */
            z-index: 1000 !important;
            background-color: var(--background-color) !important;
            margin-top: -1.5rem !important;
            padding-bottom: 0px !important;
            border-bottom: 1px solid var(--border-color) !important;
        }

        /* Forces the Tabs, Back Button, and Divider to sit with 0px gap */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(button[key^="back_btn_"]) [data-testid="stVerticalBlock"] {
            gap: 0rem !important;
        }

        /* --- 3. THE NATIVE BACK BUTTON LINK --- */
        div[data-testid="stColumn"]:has(button[key^="back_btn_"]) {
            margin-top: -22px !important;    /* Pulls button up closer to tabs */
            margin-bottom: -22px !important; /* Pulls divider up closer to button */
        }

        div[data-testid="stColumn"] button[kind="secondary"][key^="back_btn_"] {
            border: none !important;
            background-color: transparent !important;
            color: #FF4B4B !important; 
            font-weight: 500 !important;
            font-size: 0.9rem !important;
            padding: 0 !important;
            min-height: 0 !important;   
            height: 26px !important;    
            box-shadow: none !important;
            text-align: left !important;
        }

        /* --- 4. THE DIVIDER (Pinned tightly under the Back Button) --- */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(button[key^="back_btn_"]) hr {
            margin-top: 0px !important;
            margin-bottom: 8px !important;
            border-top: 1px solid var(--border-color) !important;
        }

        /* --- 5. COMPACT CONTENT TIGHTENING --- */
        h3 {
            font-size: 1.1rem !important;
            margin-top: 5px !important;
            margin-bottom: 5px !important;
        }
        
        /* Prevent auto-zoom on mobile focus */
        div[data-testid="stSegmentedControl"] button p {
            font-size: 16px !important;
        }
        </style>            
    """, unsafe_allow_html=True)


def finalize_action(message, icon="✅", delay=0.8):
    """
    Mobile-optimized feedback: replaces heavy dialogs with a toast 
    and a controlled delay before refreshing the UI.
    """
    # Clear cache first so the rerun reflects the newest data
    st.cache_data.clear()
    
    # Show a non-blocking toast
    st.toast(f"{icon} {message}")
    
    # A slightly longer delay (0.8s) is often better for mobile processors 
    # to ensure the toast is fully rendered before the rerun triggers.
    time.sleep(delay)
    
    st.rerun()

def apply_mobile_table_css():
    """
    Forces Streamlit tables to fit mobile screens and increases contrast.
    """
    st.markdown("""
        <style>
        /* Force table headers to stand out */
        div[data-testid="stTable"] th, div[data-testid="stDataFrame"] th {
            background-color: var(--secondary-background-color) !important;
            color: #FF4B4B !important; /* High contrast red */
            font-weight: 700 !important;
            text-transform: uppercase;
            font-size: 0.7rem;
        }

        /* Prevent horizontal scrollbars on the main page */
        .main .block-container {
            overflow-x: hidden !important;
        }

        /* Make data editor rows taller for easier tapping */
        div[data-testid="stDataFrame"] div[role="row"] {
            height: 45px !important;
        }
        </style>
    """, unsafe_allow_html=True)

# utils.py

def nav_callback(page_title, tab_name):
    """Callback to safely update state before page switch."""
    if page_title == "Tracker":
        st.session_state["tracker_view_selector"] = tab_name
    elif page_title == "Configure":
        st.session_state["config_tab_selection"] = tab_name

def render_back_button(target_page_title="Tracker", target_tab="Overview", breadcrumb=""):
    """
    Renders a mobile-native 'Back' link with a callback to avoid 
    SessionState mutation errors.
    """
    with st.container():
        col_back, _ = st.columns([2, 1]) 
        with col_back:
            btn_key = f"back_btn_{target_page_title}_{target_tab}"
            label = f"〈 Back / {breadcrumb}" if breadcrumb else "〈 Back"
            
            # Use on_click and args to handle the state update safely
            if st.button(
                label, 
                type="secondary", 
                key=btn_key, 
                on_click=nav_callback, 
                args=(target_page_title, target_tab)
            ):
                # Now we only handle the page switch here
                nav_pages = st.session_state.get("nav_pages", [])
                target_page = next((p for p in nav_pages if p.title == target_page_title), None)
                
                if target_page:
                    st.switch_page(target_page)
                    # No st.rerun() needed here as switch_page handles it