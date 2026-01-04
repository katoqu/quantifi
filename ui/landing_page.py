import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize

def show_landing_page():
    """
    Refactored Dashboard: Uses modular components for visual consistency.
    """
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    
    st.markdown(f"### 🚀 Welcome, {user_display}")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Head to Settings to get started.")
        return

    cats = models.get_categories() or []
    cat_map = {c['id']: c['name'].title() for c in cats}
    
    # 1. CATEGORY NAVIGATION (One-Handed Pills)
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    
    # Key is initialized in pages.py to avoid 'Session State API' conflict
    selected_cat = st.pills(
        "📁 Categories",
        options=cat_options,
        selection_mode="single",
        key="active_cat_filter", 
        label_visibility="collapsed"
    )
    
    current_filter = selected_cat if selected_cat else "All"

    # 2. DATA PREPARATION & SORTING
    scored_metrics = []
    ts_min = pd.Timestamp.min.tz_localize('UTC') 

    for m in metrics_list:
        entries = models.get_entries(metric_id=m['id'])
        df = pd.DataFrame(entries) if entries else None
        
        # Calculate stats once per metric
        stats = visualize.get_metric_stats(df)
        
        # Use recorded_at for sorting recency
        latest_ts = pd.to_datetime(df['recorded_at'], format='mixed', utc=True).max() if df is not None else ts_min
        
        scored_metrics.append((latest_ts, m, entries, stats))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)

    # 3. FILTER & RENDER GRID
    display_metrics = [x for x in scored_metrics if current_filter == "All" or cat_map.get(x[1].get('category_id')) == current_filter]

    if not display_metrics:
        st.info(f"No metrics in '{current_filter}'.")
        return

    cols = st.columns(2)
    for i, (_, m, entries, stats) in enumerate(display_metrics):
        with cols[i % 2]:
            _render_action_card(m, cat_map, entries, stats)

@st.dialog("Advanced Analytics")
def _show_advanced_viz_dialog(metric, entries, stats):
    """
    Atomic Dialog: Shows only Trends and Visualization.
    """
    st.subheader(f"📈 {metric['name'].title()} Trends")
    
    if not stats:
        st.info("Record more data to see advanced trends.")
        return

    # Render 7D Avg and Last Change in 2 columns (removes 'Latest' redundancy)
    visualize.render_stat_row(stats, mode="advanced")
    
    st.divider()

    # Show the mobile-optimized Plotly chart
    df = pd.DataFrame(entries)
    visualize.show_visualizations(df, metric.get('unit_name', ''), metric['name'])
    
    if st.button("Go to Full History", use_container_width=True):
        st.session_state["last_active_mid"] = metric['id']
        st.query_params["metric_id"] = metric['id']
        st.rerun()

def _render_action_card(metric, cat_map, entries, stats):
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    change = stats.get('change') if stats else 0
    trend_color = "#28a745" if (change or 0) >= 0 else "#dc3545"
    
    # CSS Injection (Updated for better alignment and centering)
    st.markdown("""
        <style>
            [data-testid="stVerticalBlockBorderWrapper"] > div {
                padding-top: 0.35rem !important;
                padding-bottom: 0.35rem !important;
            }
            [data-testid="stVerticalBlockBorderWrapper"] {
                margin-bottom: -14px !important;
            }
            div[data-testid="stButton"] > button {
                display: flex !important;
                align-items: center !important;
                justify-content: center !important;
                padding: 0px !important;
                height: 36px !important;
                line-height: 1 !important;
            }
            [data-testid="column"] {
                display: flex;
                flex-direction: column;
                justify-content: center;
                min-width: 0 !important;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # Adjusted ratios to close the gap: [2.0 for name, 1.4 for value]
        c1, c2, c3, c4 = st.columns([2.0, 1.4, 0.8, 0.8])

        with c1:
            st.markdown(f"""
                <div style="line-height: 1.1; padding-left: 2px;">
                    <span style="font-size: 0.55rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;">
                        {cat_name}
                    </span><br>
                    <div style="font-size: 0.85rem; font-weight: 500; margin-top: 1px; 
                                white-space: nowrap; overflow: hidden; text-overflow: ellipsis;">
                        {m_name}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with c2:
            # Changed to text-align: left to pull it closer to column 1
            st.markdown(f"""
                <div style="text-align: left; line-height: 1.1;">
                    <span style="font-size: 0.6rem; opacity: 0.6;">Latest</span><br>
                    <div style="font-size: 1.0rem; font-weight: 700; color: {trend_color};">
                        {val_display}
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with c3:
            if st.button("➕", key=f"btn_{mid}", use_container_width=True):
                st.session_state["last_active_mid"] = mid
                st.query_params["metric_id"] = mid
                st.rerun()

        with c4:
            if st.button("📊", key=f"viz_{mid}", use_container_width=True):
                _show_advanced_viz_dialog(metric, entries, stats)