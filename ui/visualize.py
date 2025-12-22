import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import models
import numpy as np # Added for average calculation

def show_visualizations():
    st.header("Visualizations")
    
    units = models.get_units() or []
    unit_lookup = {u["id"]: u["name"].title() for u in units}

    cats = models.get_categories() or []
    cat_options = [None] + [c["id"] for c in cats]
    cat_choice = st.selectbox(
        "Filter by category", 
        options=cat_options, 
        format_func=lambda i: next((c["name"].title() for c in cats if c["id"] == i), "— all —")
    )

    metrics = models.get_metrics() or []
    if cat_choice:
        metrics = [m for m in metrics if m.get("category_id") == cat_choice]

    if not metrics:
        st.info("No metrics found for the selected category.")
        return

    for m in metrics:
        mid = m.get("id")
        m_name = m.get("name", "Unknown Metric").title()
        m_unit = unit_lookup.get(m.get("unit_id"), "Value") 
        
        entries = models.get_entries(mid) or []
        if not entries:
            continue
            
        dfe = pd.DataFrame(entries)
        dfe["recorded_at"] = pd.to_datetime(dfe["recorded_at"])
        dfe = dfe.sort_values("recorded_at")

        # --- CALCULATIONS ---
        avg_value = dfe["value"].mean()

        fig = go.Figure()

        # 1. Smoothly Fitted Line (Spline)
        fig.add_trace(go.Scatter(
            x=dfe["recorded_at"], 
            y=dfe["value"], 
            mode="lines",
            line=dict(shape='spline', smoothing=1.3, color='#1f77b4'), # Smooth blue line
            name="Trend"
        ))

        # 2. Blue Dots (Markers)
        fig.add_trace(go.Scatter(
            x=dfe["recorded_at"], 
            y=dfe["value"], 
            mode="markers",
            marker=dict(color='blue', size=8),
            name="Entries"
        ))

        # 3. Average Dotted Line
        fig.add_hline(
            y=avg_value, 
            line_dash="dot", 
            line_color="red", 
            annotation_text=f"Avg: {avg_value:.1f}", 
            annotation_position="bottom right"
        )

        fig.update_layout(
            title=f"Time Series: {m_name}",
            xaxis_title="Recorded date",
            yaxis_title=m_unit,
            margin=dict(l=20, r=20, t=40, b=20),
            height=400,
            showlegend=True
        )

        st.plotly_chart(fig, use_container_width=True)