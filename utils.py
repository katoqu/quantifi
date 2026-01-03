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
    Mobile-optimized CSS to transform st.radio into large segmented tabs.
    Optimized for reachability and tactile feedback.
    """
    st.markdown("""
        <style>
        /* 1. Main Container - Full width and centered for mobile reach */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            background-color: var(--secondary-background-color);
            padding: 5px;
            border-radius: 14px;
            border: 1px solid var(--border-color);
            width: 100%;
            max-width: 500px;
            margin: 0 auto 20px auto;
        }

        /* 2. Hide the default Streamlit radio circles */
        div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]) {
            display: none !important;
        }

        /* 3. Base Tab Style - Large hit area for thumbs */
        div[data-testid="stRadio"] label {
            flex: 1;
            text-align: center;
            background-color: transparent !important;
            padding: 14px 10px !important; /* Increased padding for easier tapping */
            border-radius: 10px !important;
            margin: 2px !important;
            cursor: pointer !important;
            border: none !important;
            transition: all 0.15s ease-in-out;
            color: var(--text-color) !important;
            opacity: 0.8;
        }

        /* 4. Tactile Feedback - Shrinks slightly when pressed */
        div[data-testid="stRadio"] label:active {
            transform: scale(0.96);
        }

        /* 5. Active Tab State - High contrast for visibility */
        div[data-testid="stRadio"] label:has(input:checked) {
            background-color: var(--background-color) !important;
            box-shadow: 0px 3px 8px rgba(0,0,0,0.15) !important;
            opacity: 1;
        }
        
        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #FF4B4B !important; /* Streamlit branding red */
            font-weight: 800 !important;
        }

        /* 6. Text Legibility - 16px prevents iOS auto-zoom on input focus */
        div[data-testid="stRadio"] label p {
            margin: 0px !important;
            font-size: 16px !important;
            letter-spacing: 0.5px;
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