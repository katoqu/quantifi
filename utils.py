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
    """
    Robust CSS to transform radio buttons into segmented tabs.
    Updated with fallback selectors to ensure active state highlighting.
    """
    st.markdown("""
        <style>
        /* 1. Main Segmented Control Container */
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

        /* 2. Hide ONLY the default radio input circle */
        div[data-testid="stRadio"] label div:first-child:not([data-testid="stMarkdownContainer"]) {
            display: none !important;
        }

        /* 3. Base Tab Style (Inactive) */
        div[data-testid="stRadio"] label {
            background-color: transparent !important;
            padding: 8px 25px !important;
            border-radius: 9px !important;
            margin: 0px 3px !important;
            cursor: pointer !important;
            border: none !important;
            transition: all 0.2s ease-in-out;
            font-weight: 500;
            color: #555;
        }

        /* 4. Active Tab Highlighting */
        /* Targets the label when the internal input is checked */
        div[data-testid="stRadio"] label:has(input[checked]),
        div[data-testid="stRadio"] label[data-checked="true"] {
            background-color: white !important;
            box-shadow: 0px 2px 8px rgba(0,0,0,0.1) !important;
            color: #FF4B4B !important;
        }

        /* Ensure label text is visible, centered, and inherit color from state */
        div[data-testid="stRadio"] label p {
            margin: 0px !important;
            font-size: 16px;
            color: inherit !important;
        }
        </style>
    """, unsafe_allow_html=True)