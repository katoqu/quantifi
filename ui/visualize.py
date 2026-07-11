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


def _compute_strength_value(row, agg_type: str) -> float:
    """Compute strength metric value from sets data based on aggregation type."""
    sets = row.get("sets")
    
    # Backward compatibility: if no sets data, use fallback
    if not sets or not isinstance(sets, list):
        base_value = float(row.get("value") or row.get("load_kg") or 0)
        if agg_type == "Total Volume":
            # Assume 3 sets of 10 reps each: Total Volume = value * 10 * 3
            return base_value * 10 * 3
        elif agg_type == "Max e1RM":
            # Assume each set has same load (value/3), reps=10, number of sets=3
            # e1RM = load * (1 + reps/30) = (value/3) * (1 + 10/30) = (value/3) * (4/3)
            per_set_load = base_value / 3
            return per_set_load * (1 + 10 / 30)
        return base_value
    
    # Extract loads and reps from sets
    set_data = []
    for s in sets:
        if s and isinstance(s, dict):
            load = float(s.get("load_kg", 0))
            reps = int(s.get("reps", 10))  # Default to 10 reps if missing
            set_data.append({"load_kg": load, "reps": reps})
    
    if not set_data:
        base_value = float(row.get("value") or row.get("load_kg") or 0)
        if agg_type == "Total Volume":
            return base_value * 10 * 3
        elif agg_type == "Max e1RM":
            per_set_load = base_value / 3
            return per_set_load * (1 + 10 / 30)
        return base_value
    
    if agg_type == "Total Volume":
        # Sum of (reps * load) for all sets
        return sum(sd["load_kg"] * sd["reps"] for sd in set_data)
    elif agg_type == "Max Load":
        # Maximum single set load
        return max(sd["load_kg"] for sd in set_data)
    elif agg_type == "Average Load":
        # Average across all sets
        return sum(sd["load_kg"] for sd in set_data) / len(set_data)
    elif agg_type == "Max e1RM":
        # Max e1RM across all sets using Epley formula: load * (1 + reps/30)
        e1rms = [sd["load_kg"] * (1 + sd["reps"] / 30) for sd in set_data]
        return max(e1rms)
    else:
        return sum(sd["load_kg"] for sd in set_data)


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


def _format_baseline_label(val: float, *, kind: str, agg_kind: str) -> str:
    return f"{val:.1f}"


def _add_baseline_reference(fig, baseline_val, baseline_label, *, kind: str, agg_kind: str, unit_suffix: str = ""):
    """Helper: add horizontal reference line with a right-side label."""
    if baseline_val is None:
        return
    label_val = _format_baseline_label(baseline_val, kind=kind, agg_kind=agg_kind)
    label = f"{baseline_label} {label_val}{unit_suffix}"
    fig.add_hline(
        y=baseline_val,
        line_dash="dash",
        line_color="rgba(100, 100, 100, 0.2)",
    )
    fig.add_annotation(
        x=1.0,
        y=baseline_val,
        xref="paper",
        yref="y",
        text=label,
        showarrow=False,
        xanchor="right",
        font=dict(size=11, color="rgba(235, 235, 235, 0.9)"),
        bgcolor="rgba(20, 20, 20, 0.6)",
        bordercolor="rgba(255, 255, 255, 0.25)",
        borderwidth=1,
        borderpad=3,
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
        return f"<b>{hover_label} (avg): %{{y:.1f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>"
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
            try:
                from streamlit.runtime.state.common import TESTING_KEY
                is_testing = TESTING_KEY in st.session_state
            except Exception:
                is_testing = False

            # Normalize any existing state (string vs list) to valid options.
            if range_key in st.session_state:
                existing = st.session_state[range_key]
                if isinstance(existing, (list, tuple)):
                    valid = [v for v in existing if v in period_options]
                    if not valid:
                        del st.session_state[range_key]
                    else:
                        st.session_state[range_key] = valid[-1]
                elif existing not in period_options:
                    del st.session_state[range_key]

            if is_testing:
                current = st.session_state.get(range_key, default_val)
                idx = period_options.index(current) if current in period_options else period_options.index(default_val)
                range_choice = st.selectbox(
                    label="Period",
                    options=period_options,
                    index=idx,
                    key=range_key,
                    label_visibility="collapsed",
                )
            else:
                range_choice = st.segmented_control(
                    label="Period",
                    options=period_options,
                    default=default_val,
                    key=range_key,
                    label_visibility="collapsed",
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

        # Strength metric aggregation toggle
        if metric_kind == "strength_session":
            strength_agg_key = f"strength_agg_{widget_key}"
            strength_agg_options = ["Total Volume", "Max Load", "Average Load", "Max e1RM"]
            default_agg = strength_agg_options[0]
            strength_agg = st.selectbox(
                "Strength metric:",
                options=strength_agg_options,
                index=0,
                key=strength_agg_key,
                label_visibility="collapsed",
                help="Choose how to visualize strength sessions",
            )
        else:
            strength_agg = None
    else:
        range_choice = external_range
        strength_agg = None

    # Apply strength metric transformation if needed
    if strength_agg and metric_kind == "strength_session" and hasattr(dfe, 'columns'):
        try:
            if "sets" in dfe.columns:
                dfe = dfe.copy()
                dfe["value"] = dfe.apply(lambda row: _compute_strength_value(row, strength_agg), axis=1)
        except Exception:
            # If transformation fails, keep original values
            pass

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

    tabs = st.tabs(["Chart", "Raw data plot"])
    chart_tab, raw_tab = tabs[0], tabs[1]

    with raw_tab:
        raw_df = filtered_df.sort_values("recorded_at").copy()
        if raw_df.empty and policy.missing_policy != "missing_is_zero":
            st.info("No raw data for this period.")
        else:
            kind_for_raw = metric_kind
            if kind_for_raw not in ("quantitative", "count", "score"):
                if unit_type == "integer_range":
                    kind_for_raw = "score"
                elif unit_type == "integer":
                    kind_for_raw = "count"
                else:
                    kind_for_raw = "quantitative"

            raw_df["value"] = pd.to_numeric(raw_df["value"], errors="coerce")
            if policy.missing_policy == "missing_is_zero":
                if kind_for_raw == "count":
                    daily_agg = "sum"
                elif kind_for_raw == "score":
                    daily_agg = "median"
                else:
                    daily_agg = policy.daily_agg
                daily_df = collapse_to_daily(raw_df, daily_agg)
                raw_df = apply_missing_policy_daily(
                    daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
                )
            else:
                raw_df = raw_df.dropna(subset=["value"])

            if raw_df.empty:
                st.info("No measured values in this period.")
            else:
                fig_raw = go.Figure()

                if kind_for_raw == "score":
                    fig_raw.add_trace(
                        go.Scatter(
                            x=raw_df["recorded_at"],
                            y=raw_df["value"],
                            mode="markers",
                            marker=dict(size=6, color="rgba(20, 20, 20, 0.65)", line=dict(color="white", width=1)),
                            name="Raw",
                            hovertemplate=f"<b>Raw: %{{y:.1f}} {m_unit}</b><br>%{{x|%d %b %Y}}<extra></extra>",
                        )
                    )
                    avg_raw = float(raw_df["value"].median())
                    fig_raw.add_hline(
                        y=avg_raw,
                        line_dash="dash",
                        line_color="rgba(100, 100, 100, 0.25)",
                    )
                    avg_label = f"Median {avg_raw:.1f}"
                    fig_raw.add_annotation(
                        x=1.0,
                        y=avg_raw,
                        xref="paper",
                        yref="y",
                        text=avg_label,
                        showarrow=False,
                        xanchor="right",
                        font=dict(size=11, color="rgba(120, 120, 120, 0.7)"),
                    )
                    rs = range_start
                    re = range_end
                    if rs is None:
                        try:
                            rs = int(math.floor(float(raw_df["value"].min())))
                        except Exception:
                            rs = 1
                    if re is None:
                        try:
                            re = int(math.ceil(float(raw_df["value"].max())))
                        except Exception:
                            re = 5
                    y0, y1 = score_yaxis_range(range_start=int(rs), range_end=int(re), missing_policy=policy.missing_policy)
                    fig_raw.update_yaxes(range=[y0, y1], dtick=1)
                else:
                    fig_raw.add_trace(
                        go.Scatter(
                            x=raw_df["recorded_at"],
                            y=raw_df["value"],
                            mode="markers",
                            marker=dict(size=6, color="#1f77b4", line=dict(color="white", width=1)),
                            name="Raw",
                            hovertemplate=f"<b>Raw: %{{y:.1f}} {m_unit}</b><br>%{{x|%d %b %Y}}<extra></extra>",
                        )
                    )
                    avg_raw = float(raw_df["value"].mean())
                    fig_raw.add_hline(
                        y=avg_raw,
                        line_dash="dash",
                        line_color="rgba(100, 100, 100, 0.25)",
                    )
                    avg_label = f"Avg {avg_raw:.1f}"
                    fig_raw.add_annotation(
                        x=1.0,
                        y=avg_raw,
                        xref="paper",
                        yref="y",
                        text=avg_label,
                        showarrow=False,
                        xanchor="right",
                        font=dict(size=11, color="rgba(120, 120, 120, 0.7)"),
                    )

                fig_raw.update_layout(
                    yaxis_title=m_unit,
                    height=260,
                    margin=dict(l=10, r=20, t=30, b=60),
                    paper_bgcolor='rgba(0,0,0,0)',
                    plot_bgcolor='rgba(0,0,0,0)',
                    showlegend=False,
                    hovermode="x",
                    xaxis=dict(
                        tickformat="%d %b",
                        nticks=8,
                        fixedrange=True,
                        tickfont=dict(color="rgba(140, 140, 140, 0.8)"),
                    ),
                )
                fig_raw.update_yaxes(fixedrange=True)
                fig_raw.update_xaxes(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    spikecolor="rgba(0,0,0,0.25)",
                    spikethickness=1,
                )
                fig_raw.update_yaxes(
                    showspikes=True,
                    spikemode="across",
                    spikesnap="cursor",
                    spikecolor="rgba(0,0,0,0.25)",
                    spikethickness=1,
                )

                st.plotly_chart(
                    fig_raw,
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

    with chart_tab:
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
    
        if is_ordinal_score and "Avg" in hover_label:
            hover_label = hover_label.replace("Avg", "Median")
    
        # Normalize values: blanks/NULLs -> NaN, numeric 0 preserved.
        filtered_df["value"] = pd.to_numeric(filtered_df["value"], errors="coerce")
    
        # Option A: single aggregation from raw data (skip daily collapse),
        # except when daily semantics are required (count/score) or missing_is_zero.
        use_daily_for_plot = policy.missing_policy == "missing_is_zero" or kind in ("count", "score")
        if use_daily_for_plot:
            if kind == "count":
                daily_agg = "sum"
            elif kind == "score":
                daily_agg = "median"
            else:
                daily_agg = policy.daily_agg
    
            daily_df = collapse_to_daily(filtered_df, daily_agg)
            if policy.missing_policy == "missing_is_zero":
                plot_input_df = apply_missing_policy_daily(
                    daily_df, start_ts=start_ts, end_ts=end_ts, missing_policy=policy.missing_policy
                )
            else:
                plot_input_df = daily_df
        else:
            plot_input_df = filtered_df[["recorded_at", "value"]].copy()
    
        plot_df, agg_kind = resample_to_plot_df(
            plot_input_df,
            freq=freq,
            kind=str(kind),
            missing_policy=policy.missing_policy,
        )
    
        baseline_label = "Median" if agg_kind == "median" else "Avg"
        baseline_val = None
        baseline_val_str = None
        baseline_series = pd.to_numeric(plot_df["value"], errors="coerce").dropna()
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
        unit = (m_unit or "").strip()
        unit_suffix = f" {unit}" if unit else ""
        if use_daily_for_plot:
            summary_series = pd.to_numeric(plot_input_df["value"], errors="coerce")
            if policy.missing_policy != "missing_is_zero":
                summary_series = summary_series.dropna()
        elif policy.missing_policy == "missing_is_zero":
            summary_series = pd.to_numeric(plot_input_df["value"], errors="coerce")
        else:
            summary_series = pd.to_numeric(filtered_df["value"], errors="coerce").dropna()
        if not summary_series.empty:
            if is_ordinal_score:
                primary_label = "Median"
                primary_val = float(summary_series.median())
            else:
                primary_label = "Average"
                primary_val = float(summary_series.mean())
    
            primary_str = f"{_format_value_for_metric(primary_val, kind=kind)}{unit_suffix}"
    
            # Primary title: just key stats
            summary_main_title = f"{'Med' if is_ordinal_score else 'Avg'} {primary_str}"
            
            # Subtitle: context (date range, point count, coverage)
            date_range_str = f"{start_ts.strftime('%d %b %Y')} – {end_ts.strftime('%d %b %Y')}"
            summary_subtitle = date_range_str

        if baseline_val_str is not None and summary_main_title:
            summary_main_title = str(m_name).title()
    
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

            # Overlay raw score points for sparse/rare data visibility.
            raw_score = filtered_df[["recorded_at", "value"]].dropna()
            if not raw_score.empty:
                fig.add_trace(
                    go.Scatter(
                        x=raw_score["recorded_at"],
                        y=raw_score["value"],
                        mode="markers",
                        marker=dict(
                            size=6,
                            color="rgba(20, 20, 20, 0.55)",
                            line=dict(color="white", width=1),
                        ),
                        name="Raw",
                        hovertemplate=f"<b>Raw: %{{y:.0f}} {m_unit}</b><br>%{{x|{hover_date_fmt}}}<extra></extra>",
                    )
                )

            _add_baseline_reference(
                fig,
                baseline_val,
                baseline_label,
                kind=str(kind),
                agg_kind=str(agg_kind),
                unit_suffix=unit_suffix,
            )

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
            _add_baseline_reference(
                fig,
                baseline_val,
                baseline_label,
                kind=str(kind),
                agg_kind=str(agg_kind),
                unit_suffix=unit_suffix,
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
                    hovertemplate=_get_hover_template(hover_label, "mean", m_unit, hover_date_fmt, "quantitative"),
                )
            )
            _add_baseline_reference(
                fig,
                baseline_val,
                baseline_label,
                kind=str(kind),
                agg_kind=str(agg_kind),
                unit_suffix=unit_suffix,
            )
    
        if trend is not None:
            fig.add_trace(
                go.Scatter(
                    x=plot_df["recorded_at"],
                    y=trend,
                    mode="lines",
                    line=dict(color="rgba(31, 119, 180, 0.3)", width=2),
                    name="Trend",
                    hoverinfo="skip",
                )
            )

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
                                layer="below",
                            )
                            current_gap_start = None

                # Handle gap at the end if it exists
                if current_gap_start is not None:
                    fig.add_vrect(
                        x0=current_gap_start,
                        x1=end_ts,
                        fillcolor="rgba(200, 200, 200, 0.02)",
                        line_width=0,
                        layer="below",
                    )

        # Add "now" indicator for trailing periods (non-All views)
        if show_pills and range_choice != "All":
            current_time = _today_utc_end()
            if current_time > start_ts and current_time < end_ts:
                fig.add_vline(
                    x=current_time,
                    line_dash="dot",
                    line_color="rgba(100, 100, 100, 0.25)",
                    line_width=1,
                )
                fig.add_annotation(
                    x=current_time,
                    y=1.05,
                    text="Today →",
                    showarrow=False,
                    xref="x",
                    yref="paper",
                    font=dict(size=11, color="rgba(180, 180, 180, 0.7)"),
                    # font=dict(size=9, color="rgba(130, 130, 130, 0.5)"),
                    xanchor="right",
                )

        # Combine title and subtitle with line break if both exist
        combined_title = summary_main_title
        if summary_subtitle:
            combined_title = f"{summary_main_title}<br><sub style='font-size: 12px; color: rgba(180, 180, 180, 0.9);'>{summary_subtitle}</sub>"
        # combined_title = f"{summary_main_title}<br><sub style='font-size: 9px; color: rgba(120, 120, 120, 0.7);'>{summary_subtitle}</sub>"

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
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
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
                    font=dict(size=14, color="rgba(200, 200, 200, 0.9)"),
                    # font=dict(size=13, color="rgba(150, 150, 150, 0.9)"),
                )
                if summary_main_title
                else None
            ),
            xaxis=dict(
                tickformat=tickformat,
                nticks=8,
                fixedrange=True,
                tickfont=dict(color="rgba(140, 140, 140, 0.8)"),
            ),
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
