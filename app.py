import streamlit as st
from ui import define_configure, capture, visualize
import models
import utils

def main_dashboard():
    st.title("QuantifI - Dashboard")

    # select metric and capture data
    metrics = models.get_metrics() or []
    if not metrics:
        st.info("No metrics defined yet. Create one in 'Define & configure'.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    metric_idx = st.selectbox("Metric to capture", options=list(range(len(metrics))), format_func=lambda i: utils.format_metric_label(metrics[i], unit_meta))
    selected_metric = metrics[metric_idx]

    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)

    # Show capture section
    capture.show_capture(selected_metric, unit_meta)

    # Show collapsible editable data table
    if dfe is not None:
        # 'label' is the text shown when collapsed; 'expanded=False' hides it by default
        with st.expander("View Editable Metric Table", expanded=False):
            editable_df = visualize.editable_metric_table(dfe, m_unit, selected_metric.get("id"))

    # Collect data for visualization and show plot
    visualize.show_visualizations(dfe, m_unit, m_name )

def settings_page():
    st.title("Settings")
    define_configure.show_define_and_configure()

# Define pages with icons
pg = st.navigation([
    st.Page(main_dashboard, title="Tracker", icon="📊"),
    st.Page(settings_page, title="Configure", icon="⚙️"),
])

pg.run()