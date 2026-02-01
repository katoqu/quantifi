import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

def build_hierarchical_annotations(plot_df, freq, range_choice=None):
    month_annotations = []
    month_dividers = [] # This will now hold our vertical lines
    year_annotations = []
    
    if plot_df is None or plot_df.empty:
        return month_annotations, month_dividers, year_annotations

    # --- YEAR DIVIDERS & LABELS ---
    if range_choice in ["Last 6 months", "Last year", "All Time"]:
        years = plot_df["recorded_at"].dt.year.unique()
        for y in years:
            y_data = plot_df[plot_df["recorded_at"].dt.year == y]
            
            # Vertical line at the start of each year (Jan 1st)
            # We only draw it if it's within our actual plot range
            year_start = pd.Timestamp(year=y, month=1, day=1, tz='UTC')
            if plot_df["recorded_at"].min() <= year_start <= plot_df["recorded_at"].max():
                month_dividers.append(dict(
                    type="line", x0=year_start, x1=year_start, y0=0, y1=1,
                    xref="x", yref="paper",
                    line=dict(color="rgba(0,0,0,0.1)", width=1, dash="dot")
                ))

            # Centered Year Label at the top
            mid_ts = y_data["recorded_at"].iloc[0] + (y_data["recorded_at"].iloc[-1] - y_data["recorded_at"].iloc[0]) / 2
            year_annotations.append(dict(
                x=mid_ts, y=1.12, text=f"<b>{y}</b>", showarrow=False, xref="x", yref="paper",
                font=dict(size=11, color="rgba(0,0,0,0.4)"), xanchor="center"
            ))

    # --- CENTERED MONTH LABEL (Last Month View) ---
    if range_choice == "Last month":
        months = plot_df["recorded_at"].dt.to_period("M").unique()
        for m in months:
            m_data = plot_df[plot_df["recorded_at"].dt.to_period("M") == m]
            mid_ts = m_data["recorded_at"].iloc[0] + (m_data["recorded_at"].iloc[-1] - m_data["recorded_at"].iloc[0]) / 2
            month_annotations.append(dict(
                x=mid_ts, y=-0.3, text=f"<b>{m_data['recorded_at'].iloc[0].strftime('%B')}</b>",
                showarrow=False, xref="x", yref="paper",
                font=dict(size=12, color="rgba(0,0,0,0.6)"), xanchor="center"
            ))
            
    return month_annotations, month_dividers, year_annotations

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
    if dfe is None or dfe.empty:
        st.info("No data recorded for this metric yet.")
        return

    if not pd.api.types.is_datetime64_any_dtype(dfe['recorded_at']):
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], format='mixed', utc=True)

    range_choice = st.pills(
        "Time Range",
        options=["Last month", "Last 6 months", "Last year", "All Time"],
        default="Last month",
        key="viz_range_pills",
        label_visibility="collapsed"
    )

    last_ts = dfe["recorded_at"].max()
    
    # --- DYNAMIC LABELING LOGIC ---
    # We define what the "dot" actually represents based on the frequency
    if range_choice == "Last month":
        start_ts = last_ts - pd.Timedelta(days=31)
        freq = "1D"
        tickformat = "%d" 
        dtick = 7 * 24 * 60 * 60 * 1000 
        hover_label = "Daily Value"
        date_hover = "%d %b"
        
    elif range_choice in ["Last 6 months", "Last year"]:
        start_ts = last_ts - pd.DateOffset(months=6 if range_choice == "Last 6 months" else 12)
        freq = "W"
        tickformat = "%b"
        dtick = "M1"
        hover_label = "Weekly Avg"
        date_hover = "Week %W, %Y"
        
    else: # "All Time"
        start_ts = dfe["recorded_at"].min()
        delta_days = (last_ts - start_ts).days
        if delta_days > 180:
            freq = "M"
            hover_label = "Monthly Avg"
            date_hover = "%b %Y"
        else:
            freq = "W"
            hover_label = "Weekly Avg"
            date_hover = "Week %W, %Y"
            
        tickformat = "%b"
        dtick = "M3" if delta_days > 730 else "M1"

    # Filter and Resample
    mask = (dfe["recorded_at"] >= start_ts)
    filtered_df = dfe.loc[mask].copy().sort_values("recorded_at")
    avg_val = dfe["value"].mean() if range_choice == "All Time" else filtered_df["value"].mean()
    plot_df = filtered_df.set_index("recorded_at").resample(freq).mean(numeric_only=True).dropna().reset_index()

    # Trend calculation
    trend = None
    if range_choice in ["Last 6 months", "Last year", "All Time"]:
        trend_span = min(5, len(plot_df))
        if trend_span >= 3:
            trend = plot_df["value"].ewm(span=trend_span, adjust=False).mean()

    month_annotations, month_dividers, year_annotations = build_hierarchical_annotations(plot_df, freq, range_choice)

    fig = go.Figure()

    # 1. Main Data Trace with Dynamic Hover Labels
    fig.add_trace(go.Scatter(
        x=plot_df["recorded_at"], 
        y=plot_df["value"], 
        mode="lines+markers" if len(plot_df) < 53 else "lines",
        line=dict(shape='spline', smoothing=0.8, color='#1f77b4', width=3),
        marker=dict(size=6, color='#1f77b4', line=dict(color='white', width=1)),
        name=m_name,
        # Updated hovertemplate to show "Weekly Avg", etc.
        hovertemplate = (
            f"<b>{hover_label}: %{{y:.1f}} {m_unit}</b><br>" +
            f"%{{x|{date_hover}}}<extra></extra>"
        )
    ))

    # 2. Trendline
    if trend is not None:
        fig.add_trace(go.Scatter(
            x=plot_df["recorded_at"], y=trend, mode="lines",
            line=dict(color="rgba(31, 119, 180, 0.3)", width=2),
            name="Trend", hoverinfo="skip"
        ))

    # 3. Harmonized Average Line
    fig.add_shape(
        type="line", x0=plot_df["recorded_at"].min(), x1=plot_df["recorded_at"].max(),
        y0=avg_val, y1=avg_val, line=dict(color="rgba(255, 75, 75, 0.5)", width=2, dash="dash"),
        xref="x", yref="y"
    )

    fig.add_annotation(
        x=plot_df["recorded_at"].max(), y=avg_val, text=f"Avg: {avg_val:.1f}",
        showarrow=False, xanchor="right", yanchor="bottom",
        font=dict(size=10, color="rgba(255, 75, 75, 0.8)"),
        bgcolor="rgba(255, 255, 255, 0.7)", yshift=2
    )

    # Scaling
    all_visible_y = plot_df["value"].tolist() + [avg_val]
    fig.update_layout(
        yaxis_title=m_unit,
        yaxis=dict(range=[min(all_visible_y)*0.95, max(all_visible_y)*1.05], fixedrange=True, showgrid=True, gridcolor="rgba(0,0,0,0.05)"),
        xaxis=dict(showgrid=False, tickformat=tickformat, dtick=dtick, tickangle=0, fixedrange=True, tickfont=dict(size=10, color="rgba(0,0,0,0.6)")),
        margin=dict(l=10, r=10, t=40, b=80), height=320,
        paper_bgcolor='rgba(0,0,0,0)', plot_bgcolor='rgba(0,0,0,0)', showlegend=False,
        annotations=list(fig.layout.annotations) + month_annotations + year_annotations,
        shapes=list(fig.layout.shapes) + month_dividers 
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})