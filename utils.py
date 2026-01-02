import pandas as pd
import models
import datetime as dt
import streamlit as st

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
    """Fetches entries and extracts metadata directly from metric record."""
    mid = selected_metric.get("id")
    m_name = selected_metric.get("name", "Metric").title()
    m_unit = selected_metric.get("unit_name", "")

    entries = models.get_entries(metric_id=mid)
    if not entries:
        return pd.DataFrame(), m_unit, m_name
        
    dfe = pd.DataFrame(entries)
    dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
    return dfe.sort_values("recorded_at"), m_unit, m_name

def to_datetz(date_obj):
    """Converts a date object to a datetime with a midday timestamp."""
    return dt.datetime.combine(date_obj, dt.time(12, 0))

def apply_custom_tabs_css():
    st.markdown("""
        <style>
        /* 1. Main Container - Responsive & Adaptive */
        div[data-testid="stRadio"] > div[role="radiogroup"] {
            display: flex;
            flex-direction: row;
            background-color: var(--secondary-background-color);
            padding: 4px;
            border-radius: 12px;
            border: 1px solid var(--border-color);
            width: 100%; /* Full width on mobile */
            max-width: 400px;
            margin-bottom: 20px;
        }

        /* 2. Hide the radio circle input */
        div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]) {
            display: none !important;
        }

        /* 3. Base Label (Inactive Tab) */
        div[data-testid="stRadio"] label {
            flex: 1; /* Equal width tabs on mobile */
            text-align: center;
            background-color: transparent !important;
            padding: 8px 10px !important;
            border-radius: 9px !important;
            margin: 2px !important;
            cursor: pointer !important;
            border: none !important;
            transition: all 0.2s ease;
            color: var(--text-color) !important;
            opacity: 0.7;
        }

        /* 4. Active Tab Highlighting */
        div[data-testid="stRadio"] label:has(input:checked) {
            background-color: var(--background-color) !important;
            box-shadow: 0px 2px 5px rgba(0,0,0,0.1) !important;
            opacity: 1;
        }
        
        div[data-testid="stRadio"] label:has(input:checked) p {
            color: #FF4B4B !important; /* Streamlit Red */
            font-weight: 700 !important;
        }

        div[data-testid="stRadio"] label p {
            margin: 0px !important;
            font-size: 14px; /* Slightly smaller for mobile */
        }
        </style>
    """, unsafe_allow_html=True)