"""Chart annotation helpers for temporal labels and dividers."""

import pandas as pd


def build_hierarchical_annotations(plot_df, freq, range_choice=None):
    """Build temporal annotations with dark-mode-safe colors."""
    month_annotations = []
    month_dividers = []
    year_annotations = []

    if plot_df is None or plot_df.empty:
        return month_annotations, month_dividers, year_annotations

    # Dark-mode safe colors: lighter grays that work in both light and dark themes
    divider_color = "rgba(100, 100, 100, 0.15)"
    year_label_color = "rgba(140, 140, 140, 0.6)"
    month_label_color = "rgba(160, 160, 160, 0.8)"

    # --- YEAR DIVIDERS & LABELS ---
    if range_choice in ["Year", "All", "Custom"]:
        years = plot_df["recorded_at"].dt.year.unique()

        if len(years) > 1:
            for y in years:
                y_data = plot_df[plot_df["recorded_at"].dt.year == y]
                if y_data.empty:
                    continue

                year_start = pd.Timestamp(year=y, month=1, day=1, tz="UTC")

                if year_start > plot_df["recorded_at"].min() and year_start < plot_df["recorded_at"].max():
                    month_dividers.append(
                        dict(
                            type="line",
                            x0=year_start,
                            x1=year_start,
                            y0=0,
                            y1=1,
                            xref="x",
                            yref="paper",
                            line=dict(color=divider_color, width=1, dash="dot"),
                        )
                    )

                mid_ts = y_data["recorded_at"].iloc[0] + (
                    y_data["recorded_at"].iloc[-1] - y_data["recorded_at"].iloc[0]
                ) / 2
                year_annotations.append(
                    dict(
                        x=mid_ts,
                        y=1.18,
                        text=f"<b>{y}</b>",
                        showarrow=False,
                        xref="x",
                        yref="paper",
                        font=dict(size=11, color=year_label_color),
                        xanchor="center",
                    )
                )

    # --- CENTERED MONTH LABEL (Last Month View) ---
    if range_choice == "Month":
        months = plot_df["recorded_at"].dt.to_period("M").unique()
        for m in months:
            m_data = plot_df[plot_df["recorded_at"].dt.to_period("M") == m]
            if m_data.empty:
                continue

            mid_ts = m_data["recorded_at"].iloc[0] + (
                m_data["recorded_at"].iloc[-1] - m_data["recorded_at"].iloc[0]
            ) / 2
            month_annotations.append(
                dict(
                    x=mid_ts,
                    y=-0.3,
                    text=f"<b>{m_data['recorded_at'].iloc[0].strftime('%B')}</b>",
                    showarrow=False,
                    xref="x",
                    yref="paper",
                    font=dict(size=12, color=month_label_color),
                    xanchor="center",
                )
            )

    return month_annotations, month_dividers, year_annotations
