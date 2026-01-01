import streamlit as st
import models
import utils
from ui import manage_lookups, capture, metrics, data_editor

def tracker_page():
    """Main dashboard for capturing and viewing daily metrics."""
    st.title("QuantifI - Dashboard")

    all_metrics = models.get_metrics() or []
    if not all_metrics:
        st.info("No metrics defined yet. Create one in 'Configure'.")
        return

    # Metric selection logic: No unit_meta needed
    selected_metric = metrics.select_metric(all_metrics)

    if selected_metric:
        # Render capture form and visualizations without unit_meta
        capture.show_tracker_suite(selected_metric)


def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics defined yet.")
        return

    # Simplified selection
    selected_metric = metrics.select_metric(metrics_list)
    
    if selected_metric:
        # data_editor.py will also need to be updated to remove unit_meta
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """Settings page for managing categories and metric definitions."""
    st.title("Settings")
    
    cats = models.get_categories()
    
    # 1. Manage categories only (Units section removed from UI)
    manage_lookups.show_manage_lookups()
    
    # 2. Create new metrics (Passing only categories)
    metrics.show_create_metric(cats)