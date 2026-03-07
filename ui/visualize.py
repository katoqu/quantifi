import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import math

from metric_policy import DEFAULT_POLICY, MetricPolicy, resolve_metric_policy, set_missing_is_zero_override

from .chart_data import (
    ensure_recorded_at_utc,
    resolve_period,
    resample_to_plot_df,
    collapse_to_daily,
    apply_missing_policy_daily,
    score_resample_agg,
    score_yaxis_range,
)
from .chart_annotations import build_hierarchical_annotations
from .chart_stats import get_metric_stats


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


def _add_baseline_reference(fig, baseline_val, baseline_label, baseline_val_str):
    """Helper: add horizontal reference line without label."""
    if baseline_val is None:
        return
    fig.add_hline(
        y=baseline_val,
        line_dash="dash",
        line_color="rgba(100, 100, 100, 0.2)",
    )


def _get_hover_template(hover_label, agg_kind, m_unit, hover_date_fmt, kind):
    """Helper: construct aggregation-aware hover template."""
    if kind == "score":
        return (
            f"<b>{hover_label} (avg): %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
            if agg_kind == "mean"
            else f"<b>{hover_label} (median): %{{y:.0f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
        )
    elif kind == "count":
        return f"<b>{hover_label} (sum): %{{y:.0f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
    else:
        return f"<b>{hover_label} (avg): %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"


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
    colorblind_safe=False,
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
    dfe = ensure_recorded_at_utc(dfe)

    # 2. CALCULATE DATA SPAN
    min_date = dfe["recorded_at"].min()
    max_date = dfe["recorded_at"].max()

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
    
    end_ts = _today_utc_end() if show_pills else last_ts
    period = resolve_period(range_choice or "Month", min_ts=min_date, max_ts=max_date, anchor_end_ts=end_ts)
    start_ts = period.start_ts
    end_ts = period.end_ts
    freq = period.freq
    tickformat = period.tickformat
    hover_label = period.hover_label
    hover_date_fmt = period.hover_date_fmt

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
    daily_df = collapse_to_daily(filtered_df, policy.daily_agg)
    daily_df = apply_missing_policy_daily(
        daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
    )

    plot_df, agg_kind = resample_to_plot_df(
        daily_df,
        freq=freq,
        kind=str(kind),
        missing_policy=policy.missing_policy,
    )

    baseline_label = "Median" if (is_ordinal_score and agg_kind == "median") else "Avg"
    baseline_val = None
    baseline_val_str = None
    baseline_series = pd.to_numeric(daily_df["value"], errors="coerce").dropna()
    if not baseline_series.empty:
        if is_ordinal_score:
            baseline_val = float(baseline_series.mean() if agg_kind == "mean" else baseline_series.median())
            baseline_val_str = f"{baseline_val:.1f}" if agg_kind == "mean" else f"{baseline_val:.0f}"
        elif is_count:
            baseline_val = float(baseline_series.mean())
            baseline_val_str = f"{baseline_val:.0f}"
        else:
            baseline_val = float(baseline_series.mean())
            baseline_val_str = f"{baseline_val:.1f}"

    if plot_df.empty:
        st.info("Insufficient data points in this range to display a chart.")
        return

    # Two-level title: primary stats (main) + context (subtitle)
    summary_main_title = None
    summary_subtitle = None
    summary_series = pd.to_numeric(daily_df["value"], errors="coerce")
    if policy.missing_policy != "missing_is_zero":
        summary_series = summary_series.dropna()
    if not summary_series.empty:
        primary_label = "Average"
        primary_val = float(summary_series.mean())

        latest_val = float(summary_series.iloc[-1])
        unit = (m_unit or "").strip()
        unit_suffix = f" {unit}" if unit else ""
        primary_str = f"{_format_value_for_metric(primary_val, kind=kind)}{unit_suffix}"
        latest_str = f"{_format_value_for_metric(latest_val, kind=kind)}{unit_suffix}"
        
        # Primary title: just key stats
        summary_main_title = f"{primary_label} {primary_str} · Latest {latest_str}"
        
        # Subtitle: context (date range, point count, coverage)
        date_range_str = f"{start_ts.strftime('%d %b %Y')} → {end_ts.strftime('%d %b %Y')}"
        data_point_count = len(plot_df)
        granularity_label = {
            "D": "daily",
            "W": "weekly",
            "MS": "monthly"
        }.get(freq, "points")
        
        sparsity_note = ""
        if policy.missing_policy != "missing_is_zero" and filtered_df is not None and not filtered_df.empty:
            days_span = (end_ts - start_ts).days
            actual_days = len(filtered_df["recorded_at"].dt.date.unique())
            if days_span > 0:
                coverage = (actual_days / days_span) * 100
                if coverage < 80:
                    sparsity_note = f" · {coverage:.0f}% coverage"
        
        summary_subtitle = f"{data_point_count} {granularity_label}{sparsity_note} · {date_range_str}"

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
        colorscale = ("Viridis" if higher_is_better else "Viridis_r") if colorblind_safe else ("RdYlGn" if bool(higher_is_better) else "RdYlGn_r")

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
                hovertemplate=_get_hover_template(hover_label, agg_kind, m_unit, hover_date_fmt, "score"),
            )
        )
        
        _add_baseline_reference(fig, baseline_val, baseline_label, baseline_val_str)
        
        y0, y1 = score_yaxis_range(range_start=int(rs), range_end=int(re), missing_policy=policy.missing_policy)
        fig.update_yaxes(range=[y0, y1], dtick=1)
        fig.update_layout(bargap=0.25)
    elif is_count:
        fig.add_trace(
            go.Bar(
                x=plot_df["recorded_at"],
                y=plot_df["value"],
                name=m_name,
                marker=dict(color="rgba(31, 119, 180, 0.85)", line=dict(color="rgba(255,255,255,0.9)", width=1)),
                hovertemplate=_get_hover_template(hover_label, "sum", m_unit, hover_date_fmt, "count"),
            )
        )
        _add_baseline_reference(fig, baseline_val, baseline_label, baseline_val_str)
        
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
                hovertemplate=_get_hover_template(hover_label, "mean", m_unit, hover_date_fmt, "quantitative"),
            )
        )
        _add_baseline_reference(fig, baseline_val, baseline_label, baseline_val_str)

    if trend is not None:
        fig.add_trace(go.Scatter(x=plot_df["recorded_at"], y=trend, mode="lines", line=dict(color="rgba(31, 119, 180, 0.3)", width=2), name="Trend", hoverinfo="skip"))
    
    # Add data sparsity indicator for sparse/missing data (when missing policy is ignore_missing)
    # Skip for large time spans to avoid performance issues with hundreds of rectangles
    if policy.missing_policy != "missing_is_zero" and filtered_df is not None and not filtered_df.empty:
        days_span = (end_ts - start_ts).days
        actual_days = len(filtered_df["recorded_at"].dt.date.unique())
        
        # Only show sparsity indicator for smaller time spans (< 100 days) to avoid performance issues
        if days_span < 100 and days_span > 7 and actual_days < days_span * 0.6:
            all_days = pd.date_range(start=start_ts.floor("D"), end=end_ts.floor("D"), freq="D", tz="UTC")
            # Group consecutive missing days into fewer rectangles for performance
            missing_days_set = set(filtered_df["recorded_at"].dt.date.unique())
            current_gap_start = None
            
            for day in all_days:
                day_date = day.date()
                if day_date not in missing_days_set:
                    if current_gap_start is None:
                        current_gap_start = day
                else:
                    if current_gap_start is not None:
                        # Draw a rectangle for the gap
                        gap_end = day - pd.Timedelta(days=1)
                        fig.add_vrect(
                            x0=current_gap_start,
                            x1=gap_end,
                            fillcolor="rgba(200, 200, 200, 0.02)",
                            line_width=0,
                            layer="below"
                        )
                        current_gap_start = None
            
            # Handle gap at the end if it exists
            if current_gap_start is not None:
                fig.add_vrect(
                    x0=current_gap_start,
                    x1=end_ts,
                    fillcolor="rgba(200, 200, 200, 0.02)",
                    line_width=0,
                    layer="below"
                )
    
    # Add "now" indicator for trailing periods (non-All views)
    if show_pills and range_choice != "All":
        current_time = _today_utc_end()
        if current_time > start_ts and current_time < end_ts:
            fig.add_vline(
                x=current_time,
                line_dash="dot",
                line_color="rgba(100, 100, 100, 0.25)",
                line_width=1
            )
            fig.add_annotation(
                x=current_time,
                y=1.05,
                text="Today →",
                showarrow=False,
                xref="x",
                yref="paper",
                font=dict(size=9, color="rgba(130, 130, 130, 0.5)"),
                xanchor="right"
            )

    # Combine title and subtitle with line break if both exist
    combined_title = summary_main_title
    if summary_subtitle:
        combined_title = f"{summary_main_title}<br><sub style='font-size: 9px; color: rgba(120, 120, 120, 0.7);'>{summary_subtitle}</sub>"

    # Increase top margin if year annotations are present (to avoid overlap with title)
    top_margin = 60 if summary_main_title else 40
    if year_annotations:
        top_margin = 100

    # Combine all annotations
    all_annotations = month_annotations + year_annotations

    fig.update_layout(
        yaxis_title=m_unit, 
        height=320, 
        margin=dict(l=10, r=20, t=top_margin, b=80),
        paper_bgcolor='rgba(0,0,0,0)', 
        plot_bgcolor='rgba(0,0,0,0)', 
        showlegend=False,
        hovermode="x",
        dragmode=False,
        shapes=month_dividers,
        annotations=all_annotations,
        title=(
            dict(
                text=combined_title,
                x=0.0,
                xanchor="left",
                font=dict(size=13, color="rgba(150, 150, 150, 0.9)"),
            )
            if summary_main_title
            else None
        ),
        xaxis=dict(
            tickformat=tickformat,
            nticks=8,
            fixedrange=True,
            tickfont=dict(color="rgba(140, 140, 140, 0.8)"),
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
