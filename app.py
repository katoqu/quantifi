import streamlit as st
import models
from ui import define_configure, capture, visualize

st.title("Simple Metric Tracker")

# 1) Define & configure (categories + metric/unit creation)
cats, units = define_configure.show_define_and_configure()

# 2) Capture data
capture.show_capture()

# 3) Visualizations (groupable by category)
visualize.show_visualizations()