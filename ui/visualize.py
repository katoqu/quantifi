import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

def build_hierarchical_annotations(plot_df, freq, range_choice=None):
    month_annotations = []
    month_dividers = [] 
    year_annotations = []
    
    if plot_df is None or plot_df.empty:
        return month_annotations, month_dividers, year_annotations

    # --- YEAR DIVIDERS & LABELS ---
    if range_choice in ["Last 6 months", "Last year", "All Time", "Custom"]:
        years = plot_df["recorded_at"].dt.year.unique()
        
        if len(years) > 1:
            for y in years:
                y_data = plot_df[plot_df["recorded_at"].dt.year == y]
                if y_data.empty: continue
                
                year_start = pd.Timestamp(year=y, month=1, day=1, tz='UTC')
                
                if year_start > plot_df["recorded_at"].min() and year_start < plot_df["recorded_at"].max():
                    month_dividers.append(dict(
                        type="line", x0=year_start, x1=year_start, y0=0, y1=1,
                        xref="x", yref="paper",
                        line=dict(color="rgba(0,0,0,0.1)", width=1, dash="dot")
                    ))

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
            if m_data.empty: continue
            
            mid_ts = m_data["recorded_at"].iloc[0] + (m_data["recorded_at"].iloc[-1] - m_data["recorded_at"].iloc[0]) / 2
            month_annotations.append(dict(
                x=mid_ts, y=-0.3, text=f"<b>{m_data['recorded_at'].iloc[0].strftime('%B')}</b>",
                showarrow=False, xref="x", yref="paper",
                font=dict(size=12, color="rgba(0,0,0,0.6)"), xanchor="center"
            ))
            
    return month_annotations, month_dividers, year_annotations

def get_metric_stats(df):
    if df is None or df.empty:
        return {
            "latest": 0.0, "ma7": None, "change": 0.0,
            "avg": 0.0, "count": 0, "last_date": "No Data"
        }

    if not pd.api.types.is_datetime64_any_dtype(df['recorded_at']):
        df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='mixed', utc=True)
    elif df['recorded_at'].dt.tz is None:
        df['recorded_at'] = df['recorded_at'].dt.tz_localize('UTC')
    
    df = df.sort_values("recorded_at")

    clean_series = df["value"].dropna()
    if clean_series.empty:
        return { "latest": 0.0, "ma7": None, "change": 0.0, "avg": 0.0, "count": 0, "last_date": "No Data" }

    latest_val = float(clean_series.iloc[-1])
    
    ma7 = clean_series.rolling(window=7).mean().iloc[-1] if len(clean_series) >= 7 else None
    change = float(clean_series.iloc[-1] - clean_series.iloc[-2]) if len(clean_series) >= 2 else 0.0
    last_ts = df['recorded_at'].iloc[-1]
        
    return {
        "latest": latest_val,
        "ma7": ma7,
        "change": change,
        "avg": float(clean_series.mean()),
        "count": len(df),
        "last_date": last_ts.strftime('%d %b') 
    }

def render_stat_row(stats, mode="compact"):
    if not stats:
        return

    if mode == "compact":
        st.metric(label=stats['last_date'], value=f"{stats['latest']:.1f}")
    
    elif mode == "advanced":
        ma7_val = f"{stats['ma7']:.1f}" if stats['ma7'] is not None else "—"
        latest_val = f"{stats['latest']:.1f}"
        
        ma7_diff = stats['latest'] - stats['ma7'] if stats['ma7'] is not None else 0
        ma7_color = "#28a745" if ma7_diff >= 0 else "#dc3545"
        ma7_arrow = '↑' if ma7_diff >= 0 else '↓'
        
        change_delta = stats['change'] if stats['change'] is not None else 0
        change_color = "#28a745" if change_delta >= 0 else "#dc3545"
        change_arrow = '↑' if change_delta >= 0 else '↓'

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

def show_visualizations(dfe, m_unit, m_name, show_pills=True, external_range="Last month"):
    """
    Renders the metric trend chart with adaptive scaling and safe range selection.
    """
    if dfe is None or dfe.empty or "recorded_at" not in dfe.columns:
        st.info("No data recorded for this metric yet.")
        return

    # 1. TIMEZONE & TYPE SANITY CHECK
    if not pd.api.types.is_datetime64_any_dtype(dfe['recorded_at']):
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'], format='mixed', utc=True)
    elif dfe['recorded_at'].dt.tz is None:
        dfe['recorded_at'] = dfe['recorded_at'].dt.tz_localize('UTC')

    # 2. CALCULATE DATA SPAN FOR SMART PILLS
    min_date = dfe["recorded_at"].min()
    max_date = dfe["recorded_at"].max()
    days_diff = (max_date - min_date).days

    if show_pills:
        options = ["Last Week"]
        if days_diff > 7:
            options.append("Last month")
        if days_diff > 30:
            options.append("Last 6 months")
        if days_diff > 180:
            options.append("Last year")
        options.append("All Time")

        default_val = "Last month" if "Last month" in options else "All Time"
        
        range_choice = st.pills(
            "Time Range",
            options=options,
            default=default_val,
            key="viz_range_pills",
            label_visibility="collapsed"
        )
    else:
        range_choice = external_range

    last_ts = dfe["recorded_at"].max()
    
    # 3. DYNAMIC CONFIGURATION
    
    # Default hover date format (includes day)
    hover_date_fmt = "%d %b %Y"

    if range_choice == "Last Week":
        start_ts = last_ts - pd.Timedelta(days=7)
        freq, tickformat, hover_label = "D", "%a", "Value"
        
    elif range_choice in ["Last month", "Last Month"]:
        start_ts = last_ts - pd.Timedelta(days=31)
        freq, tickformat, hover_label = "D", "%d", "Daily Value"
        
    elif range_choice in ["Last 6 months", "Last year", "Last Year"]:
        months_back = 6 if "6 months" in range_choice else 12
        start_ts = last_ts - pd.DateOffset(months=months_back)
        freq, tickformat, hover_label = "W", "%b", "Weekly Avg"
        
    else: # "All Time" or "Custom"
        start_ts = dfe["recorded_at"].min()
        
        # Adaptive Resampling for All Time based on span
        if days_diff <= 31:
             freq, tickformat, hover_label = "D", "%d %b", "Daily Value"
        elif days_diff <= 150:
             freq, tickformat, hover_label = "W", "%d %b", "Weekly Avg"
        else:
             # --- CHANGED: Use 'MS' (Month Start) to align to 1st of month ---
             freq, tickformat, hover_label = "MS", "%b '%y", "Monthly Avg"
             # --- CHANGED: Explicitly hide day in formatting ---
             hover_date_fmt = "%b %Y"

    # 4. FILTERING & DATA GUARD
    mask = (dfe["recorded_at"] >= start_ts)
    filtered_df = dfe.loc[mask].copy().sort_values("recorded_at")
    
    if filtered_df.empty:
        st.warning(f"No data found for the {range_choice} range.")
        return

    # 5. RESAMPLING
    avg_val = dfe["value"].mean() if range_choice == "All Time" else filtered_df["value"].mean()
    
    plot_df = (
        filtered_df
        .set_index("recorded_at")
        .resample(freq)
        .mean(numeric_only=True)
        .dropna()
        .reset_index()
    )

    if plot_df.empty:
        st.info("Insufficient data points in this range to display a chart.")
        return

    if range_choice in ["Last 6 months", "Last year"] and len(plot_df) < 8:
         tickformat = "%d %b"

    trend = None
    if range_choice in ["Last 6 months", "Last year", "Last Year", "All Time"]:
        trend_span = min(5, len(plot_df))
        if trend_span >= 3:
            trend = plot_df["value"].ewm(span=trend_span, adjust=False).mean()

    # 6. PLOTLY CONSTRUCTION
    month_annotations, month_dividers, year_annotations = build_hierarchical_annotations(plot_df, freq, range_choice)
    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=plot_df["recorded_at"], 
        y=plot_df["value"], 
        mode="lines+markers" if len(plot_df) < 53 else "lines",
        line=dict(shape='spline', smoothing=0.8, color='#1f77b4', width=3),
        marker=dict(size=6, color='#1f77b4', line=dict(color='white', width=1)),
        name=m_name,
        # Use the dynamic hover_date_fmt here
        hovertemplate = f"<b>{hover_label}: %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
    ))

    if trend is not None:
        fig.add_trace(go.Scatter(x=plot_df["recorded_at"], y=trend, mode="lines", line=dict(color="rgba(31, 119, 180, 0.3)", width=2), name="Trend", hoverinfo="skip"))

    fig.add_shape(type="line", x0=plot_df["recorded_at"].min(), x1=plot_df["recorded_at"].max(), y0=avg_val, y1=avg_val, line=dict(color="rgba(255, 75, 75, 0.4)", width=2, dash="dash"))

    fig.update_layout(
        yaxis_title=m_unit, 
        height=320, 
        margin=dict(l=10, r=10, t=40, b=80),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        showlegend=False,
        annotations=list(fig.layout.annotations) + month_annotations + year_annotations,
        xaxis=dict(
            tickformat=tickformat,
            nticks=8,
        )
    )

    st.plotly_chart(fig, use_container_width=True, config={'displayModeBar': False})