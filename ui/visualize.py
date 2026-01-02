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


    delta_color = "#28a745" if (delta or 0) >= 0 else "#dc3545"
    delta_str = f"<span style='color:{delta_color}; font-size: 0.8em;'>({'%+g' % delta if delta is not None else ''})</span>"
    
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; 
                    padding: 12px; border-radius: 10px; background: var(--secondary-background-color); 
                    border: 1px solid var(--border-color); margin-bottom: 20px;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.7rem; opacity: 0.8; text-transform: uppercase;">Latest</div>
                <div style="font-weight: bold; font-size: 1rem;">{latest_val:g} {delta_str}</div>
            </div>
            <div style="text-align: center; flex: 1; border-left: 1px solid var(--border-color); border-right: 1px solid var(--border-color);">
                <div style="font-size: 0.7rem; opacity: 0.8; text-transform: uppercase;">Average</div>
                <div style="font-weight: bold; font-size: 1rem;">{avg_val:.2f}</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.7rem; opacity: 0.8; text-transform: uppercase;">Entries</div>
                <div style="font-weight: bold; font-size: 1rem;">{len(dfe)}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 3. Time Series Plot (Untouched logic)
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines+markers", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4'),
        marker=dict(size=8),
        name=m_name,
        hovertemplate="<b>Date:</b> %{x}<br><b>Value:</b> %{y} " + f"{m_unit}<extra></extra>"
    ))

    fig.update_layout(
        yaxis_title=f"Value ({m_unit})",
        margin=dict(l=0, r=0, t=20, b=0),
        height=400,
        showlegend=False,
        hovermode="x unified"
    )

    st.plotly_chart(fig, use_container_width=True)