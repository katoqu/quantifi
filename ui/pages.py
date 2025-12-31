import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor

def tracker_page():
    """Main dashboard for capturing and viewing daily metrics."""
    st.title("QuantifI - Dashboard")

    # Fetch data required for selection
    all_metrics = models.get_metrics() or []
    if not all_metrics:
        st.info("No metrics defined yet. Create one in 'Configure'.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    # Metric selection logic
    metric_idx = st.selectbox(
        "Metric to capture", 
        options=list(range(len(all_metrics))), 
        format_func=lambda i: utils.format_metric_label(all_metrics[i], unit_meta)
    )
    selected_metric = all_metrics[metric_idx]

    # Render capture form and visualizations
    capture.show_tracker_suite(selected_metric, unit_meta)


def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics defined yet.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    metric_idx = st.selectbox(
        "Select metric to manage", 
        options=list(range(len(metrics_list))), 
        format_func=lambda i: utils.format_metric_label(metrics_list[i], unit_meta),
        key="edit_page_metric_select"
    )
    selected_metric = metrics_list[metric_idx]
    
    data_editor.show_data_management_suite(selected_metric, unit_meta)

def configure_page():
    """Settings page for managing categories, units, and metric definitions."""
    st.title("Settings")
    
    # Fetch lookup data
    cats = models.get_categories()
    units = models.get_units()
    
    # 1. Manage categories and units (lookups)
    manage_lookups.show_manage_lookups()
    
    # 2. Create new metrics
    metrics.show_create_metric(cats, units)