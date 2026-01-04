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

    for i, (_, m, entries, stats) in enumerate(display_metrics):
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

    # We use a URL trick: Clicking the link adds 'log_id' or 'viz_id' to the URL
    # Streamlit will detect this change and we can trigger the logic.
    log_link = f"?log_id={mid}"
    viz_link = f"?viz_id={mid}"

    st.markdown(f"""
        <style>
            .action-row {{
                display: flex;
                flex-direction: row;
                flex-wrap: nowrap;
                align-items: center;
                justify-content: space-between;
                padding: 10px;
                border: 1px solid rgba(49, 51, 63, 0.2);
                border-radius: 10px;
                margin-bottom: 8px;
                background: white;
            }}
            .info-col {{ flex: 2; min-width: 0; line-height: 1.2; }}
            .val-col {{ flex: 1; min-width: 60px; padding: 0 10px; line-height: 1.2; }}
            .btn-col {{ display: flex; gap: 8px; }}
            .icon-btn {{
                text-decoration: none;
                font-size: 1.2rem;
                width: 36px;
                height: 36px;
                display: flex;
                align-items: center;
                justify-content: center;
                background: #f0f2f6;
                border-radius: 8px;
                color: black !important;
            }}
        </style>
        
        <div class="action-row">
            <div class="info-col">
                <span style="font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;">{cat_name}</span>
                <div style="font-size: 0.9rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;">{m_name}</div>
            </div>
            <div class="val-col">
                <span style="font-size: 0.6rem; opacity: 0.6; text-transform: uppercase;">Latest</span>
                <div style="font-size: 1.1rem; font-weight: 700; color: {trend_color};">{val_display}</div>
            </div>
            <div class="btn-col">
                <a href="{log_link}" target="_self" class="icon-btn">➕</a>
                <a href="{viz_link}" target="_self" class="icon-btn">📊</a>
            </div>
        </div>
    """, unsafe_allow_html=True)

    # --- CLICK LOGIC ---
    # We check the URL parameters to see if a "button" was clicked
    params = st.query_params
    if params.get("log_id") == str(mid):
        st.session_state["last_active_mid"] = mid
        st.query_params.clear() # Clear param so it doesn't trigger again on refresh
        st.rerun()
        
    if params.get("viz_id") == str(mid):
        # Trigger your visualization dialog
        _show_advanced_viz_dialog(metric, entries, stats)
        st.query_params.clear()