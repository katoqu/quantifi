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

    # Metric selection logic
    selected_metric = metrics.select_metric(all_metrics)

    if selected_metric:
        capture.show_tracker_suite(selected_metric)


def editor_page():
    """Dedicated page for historical data management and editing."""
    st.title("Manage & Edit Data")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics defined yet.")
        return

    selected_metric = metrics.select_metric(metrics_list)
    
    if selected_metric:
        data_editor.show_data_management_suite(selected_metric)

def configure_page():
    """Settings page for managing categories and metric definitions."""
    st.title("Settings")
    
    # 1. Fetch current data
    cats = models.get_categories() or []
    metrics_list = models.get_metrics() or []
    
    # 2. Category Management (Includes the new Edit logic)
    manage_lookups.show_manage_lookups()
    
    st.divider()
    
    # 3. Metric Management (New: Edit existing metrics)
    st.header("Metrics Configuration")
    metrics.show_edit_metrics(metrics_list, cats)
    
    # 4. Create New Metric (Add new metrics)
    metrics.show_create_metric(cats)