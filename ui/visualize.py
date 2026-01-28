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
    Renders the chart with a trendline and average baseline.
    """
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        return

    # Check date column before sorting
    if not pd.api.types.is_datetime64_any_dtype(dfe['recorded_at']):
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], format='mixed', utc=True)

    # Ensure sorting
    dfe = dfe.sort_values("recorded_at")

    # View controls (aggregation vs time window)
    view_mode = st.segmented_control(
        "View",
        options=["Aggregation", "Range"],
        default="Aggregation",
        label_visibility="collapsed",
    )

    agg_choice = None
    range_choice = None
    if view_mode == "Range":
        range_choice = st.radio(
            "Range",
            options=["Last week", "Last month", "Last 6 months", "Last year"],
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )
    else:
        agg_options = ["Auto", "Daily", "Weekly", "Monthly", "Yearly"]
        agg_choice = st.radio(
            "Aggregation",
            options=agg_options,
            index=0,
            horizontal=True,
            label_visibility="collapsed",
        )

    plot_df = dfe
    is_bucketed = False
    bucket_label = None
    tickformat = None
    dtick = None
    freq = None
    freq_map = {
        "Daily": "1D",
        "Weekly": "1W",
        "Monthly": "1M",
        "Yearly": "1Y",
    }

    if view_mode == "Range":
        last_ts = dfe["recorded_at"].max()
        if range_choice == "Last week":
            start_ts = last_ts - pd.Timedelta(days=7)
            freq = "1D"
            bucket_label = "Day"
            tickformat = "%a"
            dtick = 24 * 60 * 60 * 1000
        elif range_choice == "Last month":
            start_ts = last_ts - pd.Timedelta(days=31)
            freq = "1D"
            bucket_label = "Day"
            tickformat = "%d"
            dtick = 24 * 60 * 60 * 1000
        elif range_choice == "Last 6 months":
            start_ts = last_ts - pd.DateOffset(months=6)
            freq = "1M"
            bucket_label = "Month"
            tickformat = "%b"
            dtick = "M1"
        elif range_choice == "Last year":
            start_ts = last_ts - pd.DateOffset(months=12)
            freq = "1M"
            bucket_label = "Month"
            tickformat = "%b"
            dtick = "M1"
        else:
            start_ts = dfe["recorded_at"].min()

        plot_df = dfe[dfe["recorded_at"] >= start_ts]
        is_bucketed = True
    else:
        if agg_choice == "Auto" and len(dfe) > 200:
            bucket_label = "Day"
            freq = "1D"
            tickformat = "%a"
            dtick = 24 * 60 * 60 * 1000
        elif agg_choice in freq_map:
            freq = freq_map[agg_choice]
            label_map = {
                "Daily": "Day",
                "Weekly": "Week",
                "Monthly": "Month",
                "Yearly": "Year",
            }
            bucket_label = label_map.get(agg_choice, agg_choice)
            if agg_choice == "Daily":
                tickformat = "%a"
                dtick = 24 * 60 * 60 * 1000
            elif agg_choice == "Weekly":
                tickformat = "W%W"
                dtick = 7 * 24 * 60 * 60 * 1000
            elif agg_choice == "Monthly":
                tickformat = "%b"
                dtick = "M1"
            elif agg_choice == "Yearly":
                tickformat = "%Y"
                dtick = "M12"

    if freq:
        plot_df = (
            plot_df.set_index("recorded_at")
            .resample(freq)
            .mean(numeric_only=True)
            .dropna()
            .reset_index()
        )
        is_bucketed = True

    avg_val = plot_df["value"].mean()
    trend_span = min(5, len(plot_df))
    trend = plot_df["value"].ewm(span=trend_span, adjust=False).mean() if trend_span >= 3 else None

    show_markers = len(plot_df) <= 50
    use_gl = len(plot_df) > 150
    line_width = 2 if len(plot_df) > 100 else 3
    marker_size = 6 if show_markers else 0
    scatter_cls = go.Scattergl if use_gl else go.Scatter

    fig = go.Figure()
    
    # 1. Main Data Trace
    fig.add_trace(scatter_cls(
        x=plot_df["recorded_at"], 
        y=plot_df["value"], 
        mode="lines+markers" if show_markers else "lines",
        line=dict(shape='spline', smoothing=1.0, color='#1f77b4', width=line_width),
        marker=dict(size=marker_size, color='#1f77b4', line=dict(color='white', width=1)),
        name=m_name,
        text=[f"{val:.1f} {m_unit}" for val in plot_df["value"]],
        hovertemplate="<b>%{text}</b><br>%{x|%d %b %Y}<extra></extra>"
    ))

    # 2. Add Trendline
    if trend is not None:
        fig.add_trace(go.Scatter(
            x=plot_df["recorded_at"],
            y=trend,
            mode="lines",
            line=dict(color="rgba(31, 119, 180, 0.5)", width=2),
            name="Trend",
            hoverinfo="skip"
        ))

    # 3. Add Horizontal Average Line
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
        xaxis_title=bucket_label if is_bucketed else None,
        hovermode="x unified",
        hoverlabel=dict(bgcolor="white", font_size=12, font_color="black"),
        xaxis=dict(
            showspikes=True,
            spikemode='across',
            showgrid=False,
            fixedrange=True,
            tickformat=tickformat,
            dtick=dtick,
        ),
        yaxis=dict(fixedrange=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        margin=dict(l=10, r=10, t=10, b=10),
        height=260,
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
