import streamlit as st
from ui import define_configure, capture, visualize

def main_dashboard():
    st.title("QuantifI - Dashboard")
    capture.show_capture()
    visualize.show_visualizations()

def settings_page():
    st.title("Settings")
    define_configure.show_define_and_configure()

# Define pages with icons
pg = st.navigation([
    st.Page(main_dashboard, title="Tracker", icon="📊"),
    st.Page(settings_page, title="Configure", icon="⚙️"),
])

pg.run()