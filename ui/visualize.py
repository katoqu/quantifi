import streamlit as st
import plotly.graph_objects as go
import pandas as pd

def get_metric_stats(df):
    """
    Pure logic: Returns calculated stats from a dataframe.
    Optimized for bulk data by checking types before conversion.
    """
    if df is None or df.empty:
        # Return a dictionary with defaults instead of None
        return {
            "latest": 0.0, "ma7": None, "change": 0.0,
            "avg": 0.0, "count": 0, "last_date": "No Data"
        }

    # Performance Fix: Only convert to datetime if it's not already converted
    if not pd.api.types.is_datetime64_any_dtype(df['recorded_at']):
        df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='mixed', utc=True)
    
    # Ensure data is sorted for rolling calculations
    df = df.sort_values("recorded_at")

    latest_val = float(df["value"].iloc[-1])
    
    # Calculate 7D Average (optimized for speed)
    ma7 = df['value'].rolling(window=7).mean().iloc[-1] if len(df) >= 7 else None
    
    # Calculate Period Change
    change = None
    if len(df) >= 2:
        prev_val = float(df['value'].iloc[-2])
        change = latest_val - prev_val

    last_ts = df['recorded_at'].iloc[-1]
        
    return {
        "latest": latest_val,
        "ma7": ma7,
        "change": change,
        "avg": float(df["value"].mean()),
        "count": len(df),
        "last_date": last_ts.strftime('%d %b') 
    }

def render_stat_row(stats, mode="compact"):
    """
    UI Component: Renders horizontal stats.
    Fixed: Pre-formats strings to avoid f-string ValueError.
    """
    if not stats:
        return

    if mode == "compact":
        st.metric(label=stats['last_date'], value=f"{stats['latest']:.1f}")
    
    elif mode == "advanced":
        # 1. PRE-FORMAT DISPLAY STRINGS
        # We handle the 'None' case and formatting here to keep the HTML block clean
        ma7_val = f"{stats['ma7']:.1f}" if stats['ma7'] is not None else "—"
        latest_val = f"{stats['latest']:.1f}"
        
        # Calculate deltas for color coding
        ma7_diff = stats['latest'] - stats['ma7'] if stats['ma7'] is not None else 0
        ma7_color = "#28a745" if ma7_diff >= 0 else "#dc3545"
        ma7_arrow = '↑' if ma7_diff >= 0 else '↓'
        
        change_delta = stats['change'] if stats['change'] is not None else 0
        change_color = "#28a745" if change_delta >= 0 else "#dc3545"
        change_arrow = '↑' if change_delta >= 0 else '↓'

        # 2. RENDER THE POLISHED HTML
        st.markdown(f"""
            <div style="display: flex; gap: 10px; margin-bottom: 15px;">
                <div style="flex: 1; padding: 12px; border-radius: 10px; background: var(--secondary-background-color); border: 1px solid var(--border-color); text-align: center;">
                    <div style="font-size: 0.65rem; opacity: 0.8; text-transform: uppercase; margin-bottom: 4px;">7D Average</div>
                    <div style="font-weight: bold; font-size: 1.1rem;">{ma7_val}</div>
                    <div style="font-size: 0.8rem; color: {ma7_color}; font-weight: 600;">
                        {ma7_arrow} {abs(ma7_diff):.1f}
                    </div>
                </div>
                <div style="flex: 1; padding: 12px; border-radius: 10px; background: var(--secondary-background-color); border: 1px solid var(--border-color); text-align: center;">
                    <div style="font-size: 0.65rem; opacity: 0.8; text-transform: uppercase; margin-bottom: 4px;">Last Change</div>
                    <div style="font-weight: bold; font-size: 1.1rem;">{latest_val}</div>
                    <div style="font-size: 0.8rem; color: {change_color}; font-weight: 600;">
                        {change_arrow} {abs(change_delta):.1f}
                    </div>
                </div>
            </div>
        """, unsafe_allow_html=True)

def show_visualizations(dfe, m_unit, m_name):
    """
    Renders the chart with an Average Baseline.
    """
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        return

    # Check date column before sorting
    if not pd.api.types.is_datetime64_any_dtype(dfe['recorded_at']):
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], format='mixed', utc=True)

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
        showlegend=False,
        dragmode=False
    )

    st.plotly_chart(fig, use_container_width=True, 
                    config={
                        'displayModeBar': False, 
                        'scrollZoom': False,  # Prevents chart from hijacking scroll
                        'doubleClick': 'reset',
                        'showAxisDragHandles': False,
                        'modeBarButtonsToRemove': ['pan2d', 'zoom2d'] # Removes zoom/pan tools
                    })