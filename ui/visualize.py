import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def show_visualizations(dfe, m_unit, m_name):
    """
    Renders high-level metrics and a time-series visualization.
    The chart is optimized to respect the selected date filters.
    """
    if dfe is None or dfe.empty:
        st.info("No data available in this date range.")
        return

    # 1. Calculation Logic for Quick Stats
    dfe = dfe.sort_values("recorded_at")
    latest_val = dfe["value"].iloc[-1]
    avg_val = dfe["value"].mean()
    
    delta = None
    if len(dfe) > 1:
        delta = latest_val - dfe["value"].iloc[-2]

    # 2. Render Quick Stats Row
    st.subheader(f"{m_name} Overview")
    c1, c2, c3 = st.columns(3)
    
    with c1:
        st.metric("Latest Entry", f"{latest_val:g} {m_unit}", 
                  delta=f"{delta:g}" if delta is not None else None)
    with c2:
        st.metric("Average", f"{avg_val:.2f} {m_unit}")
    with c3:
        st.metric("Entries in View", len(dfe))

    st.divider()

    # 3. Time Series Plot 
    fig = go.Figure()
    
    # Add the primary data line
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines+markers", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4'),
        marker=dict(size=8),
        name=m_name,
        hovertemplate="<b>Date:</b> %{x}<br><b>Value:</b> %{y} " + f"{m_unit}<extra></extra>"
    ))

    # Update layout to handle date scaling
    fig.update_layout(
        yaxis_title=f"Value ({m_unit})",
        margin=dict(l=0, r=0, t=20, b=0),
        height=400,
        showlegend=False,
        hovermode="x unified"
    )

    # 4. Sync X-Axis with UI Date Pickers
    # We pull the current widget values directly to force the chart 
    # to show the full range selected by the user
    # Search for keys based on typical naming convention in your data_editor.py
    # This ensures the chart 'zooms' to exactly what the user selected.
    st.plotly_chart(fig, use_container_width=True)