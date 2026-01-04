import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize

def show_landing_page():
    """
    Refactored Dashboard: 
    - Handles Deep Links first to ensure navigation works.
    - Prevents 'Welcome' screen flash by fetching data early.
    - Uses High-Density Action Strips for mobile.
    """
# 1. FETCH DATA EARLY (Required for stats/viz in the dialog)
    metrics_list = models.get_metrics() or []
    cats = models.get_categories() or []
    cat_map = {c['id']: c['name'].title() for c in cats}

    # 2. PROCESS NAVIGATION & DIALOGS IMMEDIATELY
    if "action" in st.query_params and "mid" in st.query_params:
        action = st.query_params["action"]
        target_mid = st.query_params["mid"]
        
        if action == "viz":
            # Find the specific metric and its data for the dialog
            target_metric = next((m for m in metrics_list if str(m['id']) == target_mid), None)
            if target_metric:
                entries = models.get_entries(metric_id=target_mid)
                df = pd.DataFrame(entries) if entries else None
                stats = visualize.get_metric_stats(df)
                
                # CLEAR PARAMS SILENTLY (Without rerun) to clean the URL
                st.query_params.clear()
                
                # TRIGGER DIALOG IMMEDIATELY
                _show_advanced_viz_dialog(target_metric, entries, stats)
        
        elif action == "log":
            st.session_state["last_active_mid"] = target_mid
            st.query_params.clear()
            st.rerun() # Log action still needs rerun to switch pages/tabs

    # 2. DATA FETCHING (Ensures list is present after rerun)
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    metrics_list = models.get_metrics() or []

    # 3. RENDER HEADER
    st.markdown(f"### 🚀 Welcome, {user_display}")
    
    if not metrics_list:
        st.info("👋 Welcome! Go to Settings to create your first tracking target.")
        return

    # 4. CATEGORY NAVIGATION
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    selected_cat = st.pills(
        "📁 Categories",
        options=cat_options,
        selection_mode="single",
        key="active_cat_filter", 
        label_visibility="collapsed"
    )
    current_filter = selected_cat if selected_cat else "All"

    # 5. DATA PREPARATION & SORTING
    scored_metrics = []
    ts_min = pd.Timestamp.min.tz_localize('UTC') 

    for m in metrics_list:
        entries = models.get_entries(metric_id=m['id'])
        df = pd.DataFrame(entries) if entries else None
        stats = visualize.get_metric_stats(df)
        latest_ts = pd.to_datetime(df['recorded_at'], format='mixed', utc=True).max() if df is not None else ts_min
        scored_metrics.append((latest_ts, m, entries, stats))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)
    display_metrics = [x for x in scored_metrics if current_filter == "All" or cat_map.get(x[1].get('category_id')) == current_filter]

    if not display_metrics:
        st.info(f"No metrics in '{current_filter}'.")
        return

    # 6. RENDER THE GRID
    for _, m, entries, stats in display_metrics:           
        _render_action_card(m, cat_map, entries, stats)

@st.dialog("Advanced Analytics")
def _show_advanced_viz_dialog(metric, entries, stats):
    st.subheader(f"📈 {metric['name'].title()} Trends")
    if not stats:
        st.info("Record more data to see advanced trends.")
        return

    visualize.render_stat_row(stats, mode="advanced")
    st.divider()
    df = pd.DataFrame(entries)
    visualize.show_visualizations(df, metric.get('unit_name', ''), metric['name'])
    
    if st.button("Go to Full History", use_container_width=True):
        st.session_state["last_active_mid"] = metric['id']
        st.query_params["metric_id"] = metric['id']
        st.rerun()

def _render_action_card(metric, cat_map, entries, stats):
    """
    The High-Density Strip with the 'Nuclear' Border Fix.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    st.markdown(f"""
        <style>
            .action-row {{
                display: flex;
                flex-direction: row;
                flex-wrap: nowrap;
                align-items: center;
                justify-content: space-between;
                padding: 16px 12px; 
                border: 1px solid var(--border-color); 
                border-radius: 12px;
                margin-bottom: 10px;
                background-color: var(--secondary-background-color);
                overflow: visible !important;
            }}
            
            a.icon-btn {{
                text-decoration: none !important;
                display: inline-flex !important;
                align-items: center !important;
                justify-content: center !important;
                width: 40px !important;
                height: 40px !important;
                border-radius: 10px;
                box-sizing: border-box !important;
                line-height: 0 !important; /* CRITICAL: Prevents bottom border clipping */
                transition: transform 0.1s;
            }}
            
            a.icon-btn:active {{ transform: scale(0.92); }}

            a.icon-btn span {{
                font-size: 1.2rem;
                line-height: 0 !important;
                display: block;
                text-decoration: none !important;
            }}

            .log-btn {{
                background: rgba(40, 167, 69, 0.12);
                border: 1.5px solid #28a745 !important;
                color: #28a745 !important;
            }}
            
            .viz-btn {{
                background: var(--background-color);
                border: 1.5px solid var(--border-color) !important;
                color: var(--text-color) !important;
            }}
        </style>
        
        <div class="action-row">
            <div style="flex: 2; min-width: 0;">
                <span style="font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase; display: block;">{cat_name}</span>
                <div style="font-size: 0.95rem; font-weight: 600; overflow: hidden; text-overflow: ellipsis; white-space: nowrap; color: var(--text-color);">{m_name}</div>
            </div>
            <div style="flex: 1; min-width: 75px; padding: 0 10px;">
                <span style="font-size: 0.6rem; color: var(--text-color); opacity: 0.7; text-transform: uppercase; display: block;">Latest</span>
                <div style="font-size: 1.1rem; font-weight: 800; color: {trend_color}; line-height: 1;">{val_display}</div>
            </div>
            <div style="display: flex; gap: 10px; align-items: center;">
                <a href="?metric_id={mid}" target="_self" class="icon-btn log-btn"><span>➕</span></a>
                <a href="?action=viz&mid={mid}" target="_self" class="icon-btn viz-btn"><span>📊</span></a>
            </div>
        </div>
    """, unsafe_allow_html=True)