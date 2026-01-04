import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def get_metric_stats(df):
    """Pure logic: Returns calculated stats from a dataframe with robust date handling."""
    if df is None or df.empty:
        return None

    # Force datetime conversion to avoid 'str' attribute errors
    df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='mixed', utc=True)
    df = df.sort_values("recorded_at")

    latest_val = df["value"].iloc[-1]
    
    # Calculate 7D Average
    ma7 = df['value'].rolling(window=7).mean().iloc[-1] if len(df) >= 7 else None
    
    # Calculate Period Change
    change = None
    if len(df) >= 2:
        prev_val = df['value'].iloc[-2]
        change = latest_val - prev_val

    last_ts = df['recorded_at'].iloc[-1]
        
    return {
        "latest": latest_val,
        "ma7": ma7,
        "change": change,
        "avg": df["value"].mean(),
        "count": len(df),
        "last_date": last_ts.strftime('%d %b') 
    }

def render_stat_row(stats, mode="compact"):
    """UI Component: Renders horizontal stats, resolving redundancy."""
    if not stats:
        return

    if mode == "compact":
        # Card View: Essential current state
        st.metric(label=stats['last_date'], value=f"{stats['latest']:.1f}")
    
    elif mode == "advanced":
        # Dialog View: Trend-focused 2-column layout
        c1, c2 = st.columns(2)
        if stats['ma7'] is not None:
            diff = stats['latest'] - stats['ma7']
            c1.metric("7D Avg", f"{stats['ma7']:.1f}", delta=f"{diff:.1f}", delta_color="inverse")
        if stats['change'] is not None:
            c2.metric("Last Change", f"{stats['latest']:.1f}", delta=f"{stats['change']:.1f}")

def show_visualizations(dfe, m_unit, m_name):
    """
    Renders the chart with an Average Baseline.
    """
    if dfe is None or dfe.empty:
        st.info("No data available.")
        return

    # Ensure sorting and calculate average
    dfe = dfe.sort_values("recorded_at")
    avg_val = dfe["value"].mean()

    fig = go.Figure()
    
    # 1. Main Data Trace
    fig.add_trace(go.Scatter(
        x=dfe["recorded_at"], 
        y=dfe["value"], 
        mode="lines+markers", 
        line=dict(shape='spline', smoothing=1.3, color='#1f77b4', width=3),
        marker=dict(size=10, color='#1f77b4', line=dict(color='white', width=2)),
        name=m_name,
        text=[f"{val:.1f} {m_unit}" for val in dfe["value"]],
        hovertemplate="<b>%{text}</b><extra></extra>"
    ))

    # 2. Add Horizontal Average Line (New Logic)
    fig.add_hline(
        y=avg_val, 
        line_dash="dash", 
        line_color="rgba(255, 75, 75, 0.5)", 
        annotation_text=f"Avg: {avg_val:.1f}", 
        annotation_position="bottom right",
        annotation_font_color="rgba(255, 75, 75, 0.8)"
    )

    fig.update_layout(
        yaxis_title=f"Value ({m_unit})",
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=16, font_color="black"),
        xaxis=dict(showspikes=True, spikemode='across', showgrid=False, fixedrange=True),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=300,
        paper_bgcolor='rgba(0,0,0,0)',
        plot_bgcolor='rgba(0,0,0,0)',
        showlegend=False
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})