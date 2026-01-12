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
    st.markdown("""
        <style>
        /* --- 1. THE STICKY HEADER CONTAINER --- */
        /* Targets the container wrapping the segmented control and pills */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stPills"]) {
            position: sticky !important;
            top: 2.85rem !important;
            z-index: 1000 !important;
            background-color: var(--background-color) !important;
            margin-top: -1.5rem !important;
            padding-bottom: 5px !important;
            border-bottom: 1px solid var(--border-color) !important;
        }

        /* 2. REMOVE INTERNAL GAP between segmented control and pills */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stPills"]) [data-testid="stVerticalBlock"] {
            gap: 0rem !important;
        }

        /* 3. TIGHTEN PILL MARGINS */
        div[data-testid="stPills"] {
            margin-top: -10px !important;
            margin-bottom: -10px !important;
        }

        /* 4. PIN DIVIDER TO PILL */
        div[data-testid="stVerticalBlockBorderWrapper"]:has(div[data-testid="stPills"]) hr {
            margin-top: 5px !important;
            margin-bottom: 5px !important;
        }
        </style>            
    """, unsafe_allow_html=True)

def finalize_action(message, icon="✅"):
    """
    Refined for performance: Clears cache and shows a toast.
    The natural Streamlit rerun triggered by the button click 
    will handle the UI refresh without 'double-hopping'.
    """
    st.cache_data.clear()
    st.toast(f"{icon} {message}")
    # Removed time.sleep() and st.rerun() to prevent redundant mobile refreshes.

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

def render_back_button(target_page_title="Tracker", target_tab="Overview"):
    """
    Renders a simple native Streamlit pill as a 'Back to Start' button.
    """
    label = "〈 Back to Start" # Simplified label
    
    st.pills(
        "Navigation",
        options=[label],
        key=f"pnav_{target_page_title}_{target_tab}",
        label_visibility="collapsed",
        selection_mode="single"
    )

# In utils.py
def apply_landing_grid_css():
    # REFINED CSS: Added vertical spacing for pills and grid padding
    st.markdown("""
    <style>
            /* 1. SHRINK THE CONTAINER BOX: Targets the inner padding of the border */
            [data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 4px 10px !important; 
            }

            /* 2. THE 50/50 GRID: Split the flex space equally, lock buttons to 100px */
            .action-card-grid {
                display: grid !important;
                grid-template-columns: 2fr 1fr 100px !important; 
                align-items: center !important;
                width: 100%;
                gap: 0px !important;
            }

            /* 3. TIGHTEN TEXT: Reduce vertical space between lines */
            .metric-identity {
                line-height: 1.2 !important;
                min-width: 0;
            }

            .value-box {
                justify-self: start; 
                border-left: 1px solid rgba(128,128,128,0.2); 
                padding-left: 10px;
                line-height: 1.0;
                text-align: left;
            }

            div[data-testid="stPills"] { 
                margin-top: 4px !important; 
                display: flex;
                justify-content: flex-end;
            }
        </style>
    """, unsafe_allow_html=True)
