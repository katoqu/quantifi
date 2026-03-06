import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

from metric_policy import DEFAULT_POLICY, MetricPolicy, resolve_metric_policy, set_missing_is_zero_override


def _ensure_recorded_at_utc(df: pd.DataFrame) -> pd.DataFrame:
    if df is None or df.empty:
        return df
    if not pd.api.types.is_datetime64_any_dtype(df["recorded_at"]):
        df["recorded_at"] = pd.to_datetime(df["recorded_at"], format="mixed", utc=True)
    elif df["recorded_at"].dt.tz is None:
        df["recorded_at"] = df["recorded_at"].dt.tz_localize("UTC")
    return df


def _stable_metric_key(metric_id: str | None, metric_name: str | None) -> str:
    if metric_id:
        return str(metric_id).strip()
    return (metric_name or "").strip().lower()


def _today_utc_end() -> pd.Timestamp:
    # End-of-today (UTC) so day-bucketed charts include the current day.
    today = pd.Timestamp.now(tz="UTC").floor("D")
    return today + pd.Timedelta(days=1) - pd.Timedelta(microseconds=1)


def _format_value_for_metric(val: float | None, *, kind: str) -> str:
    if val is None or (isinstance(val, float) and pd.isna(val)):
        return "—"
    if kind == "count":
        try:
            return f"{int(round(float(val)))}"
        except Exception:
            return str(val)
    try:
        return f"{float(val):.1f}"
    except Exception:
        return str(val)


def _score_resample_agg(*, missing_policy: str) -> str:
    return "mean" if missing_policy == "missing_is_zero" else "median"


def _score_yaxis_range(*, range_start: int, range_end: int, missing_policy: str) -> tuple[float, float]:
    if missing_policy == "missing_is_zero":
        range_start = min(int(range_start), 0)
    return (float(range_start) - 0.5, float(range_end) + 0.5)


def _collapse_to_daily(df: pd.DataFrame, daily_agg: str) -> pd.DataFrame:
    if df is None or df.empty:
        return pd.DataFrame(columns=["recorded_at", "value"])

    df = df.sort_values("recorded_at").copy()
    df["value"] = pd.to_numeric(df["value"], errors="coerce")
    df["_day"] = df["recorded_at"].dt.floor("D")

    if daily_agg == "mean":
        agg_func = "mean"
    elif daily_agg == "last":
        agg_func = lambda s: s.dropna().iloc[-1] if s.dropna().shape[0] else float("nan")
    elif daily_agg == "max":
        agg_func = "max"
    elif daily_agg == "min":
        agg_func = "min"
    else:
        agg_func = lambda s: s.sum(min_count=1)

    daily = (
        df.groupby("_day", as_index=False)["value"]
        .agg(agg_func)
        .rename(columns={"_day": "recorded_at"})
    )
    return daily[["recorded_at", "value"]]


def _apply_missing_policy_daily(
    daily_df: pd.DataFrame, *, start_ts: pd.Timestamp, end_ts: pd.Timestamp, missing_policy: str
) -> pd.DataFrame:
    if missing_policy != "missing_is_zero":
        return daily_df

    start_day = start_ts.floor("D")
    end_day = end_ts.floor("D")
    if pd.isna(start_day) or pd.isna(end_day) or start_day > end_day:
        return daily_df

    all_days = pd.date_range(start=start_day, end=end_day, freq="D", tz="UTC")
    filled = (
        daily_df.set_index("recorded_at")["value"]
        .reindex(all_days)
        .fillna(0.0)
        .rename_axis("recorded_at")
        .reset_index()
    )
    return filled[["recorded_at", "value"]]

def build_hierarchical_annotations(plot_df, freq, range_choice=None):
    month_annotations = []
    month_dividers = [] 
    year_annotations = []
    
    if plot_df is None or plot_df.empty:
        return month_annotations, month_dividers, year_annotations

    # --- YEAR DIVIDERS & LABELS ---
    if range_choice in ["Year", "All", "Custom"]:
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
    if range_choice == "Month":
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

def get_metric_stats(df, *, policy: MetricPolicy | None = None):
    if df is None or df.empty:
        return {
            "latest": None, "ma7": None, "change": None,
            "avg": None, "count": 0, "last_date": "No Data"
        }

    policy = policy or DEFAULT_POLICY
    df = df.copy()
    df = _ensure_recorded_at_utc(df)
    
    df = df.sort_values("recorded_at")

    # Treat NULL/blank as "not measured" (excluded from stats), but keep numeric 0 as valid.
    raw_numeric = pd.to_numeric(df["value"], errors="coerce")
    clean_series = raw_numeric.dropna()
    if clean_series.empty:
        return {
            "latest": None,
            "ma7": None,
            "change": None,
            "avg": None,
            "count": 0,
            "last_date": "No Data",
        }

    last_ts = df.loc[clean_series.index[-1], "recorded_at"]

    if policy.missing_policy == "missing_is_zero":
        start_ts = df["recorded_at"].min()
        end_ts = df["recorded_at"].max()
        daily_df = _collapse_to_daily(df, policy.daily_agg)
        daily_df = _apply_missing_policy_daily(
            daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
        )
        series = pd.to_numeric(daily_df["value"], errors="coerce").fillna(0.0)

        latest_val = float(series.iloc[-1])
        ma7 = series.rolling(window=7).mean().iloc[-1] if series.shape[0] >= 7 else None
        change = float(series.iloc[-1] - series.iloc[-2]) if series.shape[0] >= 2 else 0.0
        avg_val = float(series.mean())
    else:
        latest_val = float(clean_series.iloc[-1])
        ma7 = clean_series.rolling(window=7).mean().iloc[-1] if len(clean_series) >= 7 else None
        change = float(clean_series.iloc[-1] - clean_series.iloc[-2]) if len(clean_series) >= 2 else 0.0
        avg_val = float(clean_series.mean())
        
    return {
        "latest": latest_val,
        "ma7": ma7,
        "change": change,
        "avg": avg_val,
        "count": int(clean_series.shape[0]),
        "last_date": last_ts.strftime('%d %b') 
    }

def render_stat_row(stats, mode="compact"):
    if not stats:
        return

    if mode == "compact":
        if stats.get("count", 0) <= 0 or stats.get("latest") is None:
            st.metric(label=stats.get("last_date") or "—", value="—")
        else:
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

def show_visualizations(
    dfe,
    m_unit,
    m_name,
    *,
    metric_kind=None,
    unit_type="float",
    range_start=None,
    range_end=None,
    higher_is_better=True,
    show_pills=True,
    external_range="Month",
    policy: MetricPolicy | None = None,
    metric_id: str | None = None,
):
    """
    Renders the metric trend chart with adaptive scaling and safe range selection.
    """
    if dfe is None or dfe.empty or "recorded_at" not in dfe.columns:
        st.info("No data recorded for this metric yet.")
        return

    policy = policy or resolve_metric_policy(m_name, metric_id=metric_id) or DEFAULT_POLICY
    dfe = dfe.copy()

    # 1. TIMEZONE & TYPE SANITY CHECK
    dfe = _ensure_recorded_at_utc(dfe)

    # 2. CALCULATE DATA SPAN
    min_date = dfe["recorded_at"].min()
    max_date = dfe["recorded_at"].max()
    days_diff = (max_date - min_date).days

    # Stable per-metric keys (avoid casing/page differences breaking widget state).
    widget_key = _stable_metric_key(metric_id, str(m_name))

    if show_pills:
        period_options = ["Week", "Month", "6M", "Year", "All"]
        default_val = "Month"

        range_key = f"viz_period_{widget_key}"
        zeros_key = f"viz_zeros_{widget_key}"

        c1, c2 = st.columns([5, 1], vertical_alignment="center")
        with c1:
            if range_key in st.session_state and st.session_state[range_key] not in period_options:
                del st.session_state[range_key]
            range_choice = st.segmented_control(
                label="",
                options=period_options,
                default=default_val,
                key=range_key,
            )
        with c2:
            initial_missing_is_zero = policy.missing_policy == "missing_is_zero"
            missing_is_zero = st.toggle(
                "Zeros",
                value=bool(initial_missing_is_zero),
                key=zeros_key,
                help="Fill missing days as 0 (best for habits/totals). Leave off for measurements.",
            )
            set_missing_is_zero_override(metric_name=m_name, metric_id=metric_id, enabled=missing_is_zero)
            if bool(missing_is_zero) != bool(initial_missing_is_zero):
                policy = MetricPolicy(
                    missing_policy="missing_is_zero" if missing_is_zero else "ignore_missing",
                    daily_agg=policy.daily_agg,
                )
    else:
        range_choice = external_range

    last_ts = dfe["recorded_at"].max()
    
    # 3. DYNAMIC CONFIGURATION
    
    # Default hover date format (includes day)
    hover_date_fmt = "%d %b %Y"

    end_ts = _today_utc_end() if show_pills else last_ts

    if range_choice == "Week":
        start_ts = end_ts - pd.Timedelta(days=7)
        freq, tickformat, hover_label = "D", "%a", "Value"
        
    elif range_choice in ["Month"]:
        start_ts = end_ts - pd.Timedelta(days=31)
        freq, tickformat, hover_label = "D", "%d", "Daily Value"

    elif range_choice in ["6M", "6m", "Last 6 months", "Last 6 Months"]:
        start_ts = end_ts - pd.DateOffset(months=6)
        freq, tickformat, hover_label = "W", "%d %b", "Weekly Avg"
        
    elif range_choice == "Year":
        start_ts = end_ts - pd.DateOffset(months=12)
        freq, tickformat, hover_label = "W", "%b", "Weekly Avg"        
    else: # "All" or "Custom"
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
    mask = (dfe["recorded_at"] >= start_ts) & (dfe["recorded_at"] <= end_ts)
    filtered_df = dfe.loc[mask].copy().sort_values("recorded_at")
    
    if filtered_df.empty and policy.missing_policy != "missing_is_zero":
        st.info("No measurements recorded in this period.")
        return

    # 5. RESAMPLING
    kind = metric_kind
    if kind not in ("quantitative", "count", "score"):
        if unit_type == "integer_range":
            kind = "score"
        elif unit_type == "integer":
            kind = "count"
        else:
            kind = "quantitative"

    is_ordinal_score = kind == "score"
    is_count = kind == "count"

    # Normalize values: blanks/NULLs -> NaN, numeric 0 preserved.
    filtered_df["value"] = pd.to_numeric(filtered_df["value"], errors="coerce")
    daily_df = _collapse_to_daily(filtered_df, policy.daily_agg)
    daily_df = _apply_missing_policy_daily(
        daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
    )

    if is_ordinal_score:
        # If missing days are filled as 0, median tends to collapse toward 0 for sparse series
        # (and can hide real recordings in long "All" ranges). Mean preserves signal while
        # still reflecting "zeros" semantics.
        agg_func = _score_resample_agg(missing_policy=policy.missing_policy)
    elif is_count:
        # Avoid turning "all missing" buckets into 0.
        agg_func = lambda s: s.sum(min_count=1)
    else:
        agg_func = "mean"

    baseline_label = "Median" if (is_ordinal_score and agg_func == "median") else "Avg"
    baseline_val = None
    baseline_val_str = None
    baseline_series = pd.to_numeric(daily_df["value"], errors="coerce").dropna()
    if not baseline_series.empty:
        if is_ordinal_score:
            baseline_val = float(baseline_series.mean() if agg_func == "mean" else baseline_series.median())
            baseline_val_str = f"{baseline_val:.1f}" if agg_func == "mean" else f"{baseline_val:.0f}"
        elif is_count:
            baseline_val = float(baseline_series.mean())
            baseline_val_str = f"{baseline_val:.0f}"
        else:
            baseline_val = float(baseline_series.mean())
            baseline_val_str = f"{baseline_val:.1f}"

    plot_df = (
        daily_df.set_index("recorded_at")
        .resample(freq)[["value"]]
        .agg(agg_func)
        .dropna(subset=["value"])
        .reset_index()
    )

    if plot_df.empty:
        st.info("Insufficient data points in this range to display a chart.")
        return

    # Apple-like summary: primary stat for the selected period + latest value.
    summary_series = pd.to_numeric(daily_df["value"], errors="coerce")
    if policy.missing_policy != "missing_is_zero":
        summary_series = summary_series.dropna()
    if not summary_series.empty:
        if kind == "count":
            primary_label = "Total"
            primary_val = float(summary_series.sum())
        else:
            primary_label = "Average"
            primary_val = float(summary_series.mean())

        latest_val = float(summary_series.iloc[-1])
        unit = (m_unit or "").strip()
        unit_suffix = f" {unit}" if unit else ""

        s1, s2 = st.columns(2)
        with s1:
            st.metric(primary_label, f"{_format_value_for_metric(primary_val, kind=kind)}{unit_suffix}")
        with s2:
            st.metric("Latest", f"{_format_value_for_metric(latest_val, kind=kind)}{unit_suffix}")

    if range_choice in ["Last 6 months", "Last year"] and len(plot_df) < 8:
         tickformat = "%d %b"

    trend = None
    if kind == "quantitative" and range_choice in ["6M", "Year", "All"]:
        trend_span = min(5, len(plot_df))
        if trend_span >= 3:
            trend = plot_df["value"].ewm(span=trend_span, adjust=False).mean()

    # 6. PLOTLY CONSTRUCTION
    month_annotations, month_dividers, year_annotations = build_hierarchical_annotations(plot_df, freq, range_choice)
    fig = go.Figure()

    if is_ordinal_score:
        rs = range_start
        re = range_end
        if rs is None:
            try:
                rs = int(math.floor(float(filtered_df["value"].min())))
            except Exception:
                rs = 1
        if re is None:
            try:
                re = int(math.ceil(float(filtered_df["value"].max())))
            except Exception:
                re = 5
        colorscale = "RdYlGn" if bool(higher_is_better) else "RdYlGn_r"

        fig.add_trace(
            go.Bar(
                x=plot_df["recorded_at"],
                y=plot_df["value"],
                name=m_name,
                marker=dict(
                    color=plot_df["value"],
                    colorscale=colorscale,
                    cmin=rs,
                    cmax=re,
                    showscale=False,
                    line=dict(color="rgba(255,255,255,0.9)", width=1),
                ),
                hovertemplate=(
                    f"<b>{hover_label}: %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
                    if agg_func == "mean"
                    else f"<b>{hover_label}: %{{y:.0f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
                ),
            )
        )
        y0, y1 = _score_yaxis_range(range_start=int(rs), range_end=int(re), missing_policy=policy.missing_policy)
        fig.update_yaxes(range=[y0, y1], dtick=1)
        fig.update_layout(bargap=0.25)
    elif is_count:
        fig.add_trace(
            go.Bar(
                x=plot_df["recorded_at"],
                y=plot_df["value"],
                name=m_name,
                marker=dict(color="rgba(31, 119, 180, 0.85)", line=dict(color="rgba(255,255,255,0.9)", width=1)),
                hovertemplate=f"<b>{hover_label}: %{{y:.0f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>",
            )
        )
        fig.update_layout(bargap=0.25)
    else:
        fig.add_trace(
            go.Scatter(
                x=plot_df["recorded_at"],
                y=plot_df["value"],
                mode="lines+markers" if len(plot_df) < 53 else "lines",
                line=dict(shape="spline", smoothing=0.8, color="#1f77b4", width=3),
                marker=dict(size=6, color="#1f77b4", line=dict(color="white", width=1)),
                name=m_name,
                hovertemplate=f"<b>{hover_label}: %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>",
            )
        )

    if trend is not None:
        fig.add_trace(go.Scatter(x=plot_df["recorded_at"], y=trend, mode="lines", line=dict(color="rgba(31, 119, 180, 0.3)", width=2), name="Trend", hoverinfo="skip"))

    if baseline_val is not None and pd.notna(baseline_val):
        fig.add_shape(
            type="line",
            x0=plot_df["recorded_at"].min(),
            x1=plot_df["recorded_at"].max(),
            y0=baseline_val,
            y1=baseline_val,
            line=dict(color="rgba(255, 75, 75, 0.4)", width=2, dash="dash"),
        )
        fig.add_annotation(
            x=0.99,
            xref="paper",
            xanchor="right",
            y=baseline_val,
            yref="y",
            yanchor="bottom",
            text=f"{baseline_label} {baseline_val_str} {m_unit}".strip(),
            showarrow=False,
            font=dict(size=10, color="rgba(255, 75, 75, 0.55)"),
        )

    fig.update_layout(
        yaxis_title=m_unit, 
        height=320, 
        margin=dict(l=10, r=10, t=40, b=80),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        showlegend=False,
        annotations=list(fig.layout.annotations) + month_annotations + year_annotations,
        hovermode="x",
        dragmode="pan",
        xaxis=dict(
            tickformat=tickformat,
            nticks=8,
            fixedrange=True,
        )
    )

    fig.update_yaxes(fixedrange=True)
    fig.update_xaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="rgba(0,0,0,0.25)",
        spikethickness=1,
    )
    fig.update_yaxes(
        showspikes=True,
        spikemode="across",
        spikesnap="cursor",
        spikecolor="rgba(0,0,0,0.25)",
        spikethickness=1,
    )

    st.plotly_chart(
        fig,
        use_container_width=True,
        config={
            "displayModeBar": False,
            "staticPlot": False,
            "scrollZoom": False,
            "doubleClick": False,
            "displaylogo": False,
            "editable": False,
            "showAxisDragHandles": False,
            "showAxisRangeEntryBoxes": False,
        },
    )
