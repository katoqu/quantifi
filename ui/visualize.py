import streamlit as st
import plotly.graph_objects as go
import models
import numpy as np
from data_editor import editable_metric_table

def show_visualizations(dfe, m_unit, m_name):
    if dfe is None:
        st.warning("No data available.")
        return
    
    # 4. Time Series Plot 
    avg_value = dfe["value"].mean()
    fig = go.Figure()

    # Smooth Fitted Line (Spline)
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4'),
        name="Trend"
    ))

    # Actual Data Points
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="markers", 
        marker=dict(color='blue', size=8),
        name="Entries"
    ))

    # Dotted Average Line
    fig.add_hline(
        y=avg_value, 
        line_dash="dot", 
        line_color="red", 
        annotation_text=f"Avg: {avg_value:.1f}", 
        annotation_position="bottom right"
    )

    # Dynamic Title and Axis
    fig.update_layout(
        title=f"{m_name}",
        yaxis_title=m_unit,
        height=400,
        showlegend=True
    )

    st.plotly_chart(fig, use_container_width=True)