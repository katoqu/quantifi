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
    Merged Modern Layout: Combines tactile segmented tabs with 
    theme-aware layering to separate navigation from content.
    """
    st.markdown("""
        <style>
        /* 1. LAYER 1: NAVIGATION CONTAINER (Header Surface) */
        /* Updated to target st.segmented_control and your existing radio logic */
        div[data-testid="stSegmentedControl"], 
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex !important;
            flex-direction: row !important;
            background-color: var(--secondary-background-color) !important;
            padding: 8px !important;
            border-radius: 16px !important;
            border: 1px solid var(--border-color) !important;
            width: 100% !important;
            max-width: 500px !important;
            margin: 0 auto 12px auto !important;
        }

        /* 2. TAB BUTTON STYLING (Tactile & High Contrast) */
        /* Targets your existing radio labels and new segmented buttons */
        div[data-testid="stRadio"] label,
        div[data-testid="stSegmentedControl"] button {
            flex: 1 !important;
            text-align: center !important;
            background-color: transparent !important;
            padding: 12px 8px !important;
            border-radius: 12px !important;
            margin: 2px !important;
            border: none !important;
            transition: all 0.15s ease-in-out !important;
            color: var(--text-color) !important;
            opacity: 0.7;
        }

        /* Active State - Matches your existing branding red */
        div[data-testid="stRadio"] label:has(input:checked),
        div[data-testid="stSegmentedControl"] button[aria-selected="true"] {
            background-color: var(--background-color) !important;
            box-shadow: 0px 3px 8px rgba(0,0,0,0.12) !important;
            opacity: 1 !important;
            color: #FF4B4B !important; 
            font-weight: 800 !important;
        }

        /* 3. LAYER 2: METRIC SELECTOR (Secondary Card) */
        /* Styles the st.expander used in metrics.py to look like a separate card */
        details[data-testid="stExpander"] {
            border: 1px solid var(--border-color) !important;
            border-radius: 12px !important;
            background-color: var(--background-color) !important;
            margin-bottom: 15px !important;
            box-shadow: 0 2px 4px rgba(0,0,0,0.05) !important;
        }
        
        summary {
            padding: 10px !important;
            font-size: 0.95rem !important;
            color: var(--primary-color) !important;
            font-weight: 600 !important;
        }

        /* 4. COMPACT CONTENT TIGHTENING */
        /* Reduces vertical gaps and shrinks massive titles */
        [data-testid="stVerticalBlock"] {
            gap: 0.5rem !important;
        }

        h3, [data-testid="stMarkdownContainer"] b {
            font-size: 1rem !important;
            margin-bottom: 4px !important;
            display: inline-block;
        }

        /* Prevent auto-zoom on mobile focus */
        div[data-testid="stRadio"] label p, 
        div[data-testid="stSegmentedControl"] button p {
            font-size: 16px !important;
            margin: 0 !important;
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