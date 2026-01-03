import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def show_visualizations(dfe, m_unit, m_name):
    """
    Mobile-optimized time-series visualization.
    Reduces accidental interactions by disabling zoom/pan while
    maintaining a scanline for data details.
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
    delta_str = f"<span style='color:{delta_color}; font-size: 0.8em;'>({'%+.0f' % delta if delta is not None else ''})</span>"
    
    # Compact Stats Card
    st.markdown(f"""
        <div style="display: flex; justify-content: space-between; align-items: center; 
                    padding: 10px; border-radius: 10px; background: var(--secondary-background-color); 
                    border: 1px solid var(--border-color); margin-bottom: 15px;">
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.65rem; opacity: 0.8; text-transform: uppercase;">Latest</div>
                <div style="font-weight: bold; font-size: 0.9rem;">{latest_val:.1f} {delta_str}</div>
            </div>
            <div style="text-align: center; flex: 1; border-left: 1px solid var(--border-color); border-right: 1px solid var(--border-color);">
                <div style="font-size: 0.65rem; opacity: 0.8; text-transform: uppercase;">Average</div>
                <div style="font-weight: bold; font-size: 0.9rem;">{avg_val:.1f}</div>
            </div>
            <div style="text-align: center; flex: 1;">
                <div style="font-size: 0.65rem; opacity: 0.8; text-transform: uppercase;">Entries</div>
                <div style="font-weight: bold; font-size: 0.9rem;">{len(dfe)}</div>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # 2. Optimized Time Series Plot
    fig = go.Figure()
    
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines+markers", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4', width=3),
        marker=dict(
            size=10, 
            color='#1f77b4',
            line=dict(
                color='white',
                width=2
            )
        ),
        name=m_name,
        hovertemplate="<b>%{y:.1f}</b> " + f"{m_unit}<extra></extra>"
    ))

    fig.update_layout(
        yaxis_title=f"Value ({m_unit})",
        margin=dict(l=10, r=10, t=10, b=10), # Ultra-tight margins
        height=300, # More compact height for mobile
        showlegend=False,
        # scan-line logic:
        hovermode="x unified",
        hoverlabel=dict(bgcolor="rgba(255,255,255,0.9)", font_size=16), # Larger text for legibility
        dragmode=False, # DISBALE ZOOM/PAN (prevents accidental selection)
        xaxis=dict(
            showgrid=False, 
            fixedrange=True, # Prevent zooming on X
            tickfont=dict(size=10)
        ),
        yaxis=dict(
            showgrid=True, 
            gridcolor="rgba(0,0,0,0.05)", 
            fixedrange=True, # Prevent zooming on Y
            tickfont=dict(size=10)
        ),
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
    )

    # Disable the Plotly configuration bar entirely
    st.plotly_chart(
        fig, 
        use_container_width=True, 
        config={'displayModeBar': False, 'staticPlot': False}
    )
