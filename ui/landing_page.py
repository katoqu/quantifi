import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize

import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize

def show_landing_page(metrics_list, all_entries):
    cats = models.get_categories() or []
        
    # DIALOGS & DEEP LINKS
    if "action" in st.query_params and "mid" in st.query_params:
        _handle_query_params(metrics_list, all_entries)

    # 3. USER GREETING
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    st.markdown(f"### 🚀 Welcome, {user_display}")
    
    # RENDER FRAGMENTED GRID
    render_metric_grid(metrics_list, cats, all_entries)

@st.fragment
def render_metric_grid(metrics_list, cats, all_entries):
    """Handles pill selection and grid rendering instantly."""
    cat_map = {c['id']: c['name'].title() for c in cats}
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    
    selected_cat = st.pills(
        "📁 Categories",
        options=cat_options,
        selection_mode="single",
        key="active_cat_filter", 
        label_visibility="collapsed"
    )
    current_filter = selected_cat if selected_cat else "All"

    # Convert all entries to DataFrame once
    all_df = pd.DataFrame(all_entries)
    scored_metrics = []
    ts_min = pd.Timestamp.min.tz_localize('UTC') 

    for m in metrics_list:
        m_id = m['id']
        m_entries_df = all_df[all_df['metric_id'] == m_id] if not all_df.empty else pd.DataFrame()        
        stats = visualize.get_metric_stats(m_entries_df)
        
        # Calculate latest timestamp for sorting
        latest_ts = ts_min
        if not m_entries_df.empty:
            latest_ts = pd.to_datetime(m_entries_df['recorded_at'], format='mixed', utc=True).max()
        
        scored_metrics.append((latest_ts, m, m_entries_df, stats))
    
    # Sort by recent activity
    scored_metrics.sort(key=lambda x: x[0], reverse=True)
    
    # Filter by category
    display_metrics = [
        x for x in scored_metrics 
        if current_filter == "All" or cat_map.get(x[1].get('category_id')) == current_filter
    ]

    if not display_metrics:
        st.info(f"No metrics in '{current_filter}'.")
        return

    for _, m, entries_df, stats in display_metrics:           
        _render_action_card(m, cat_map, entries_df.to_dict('records'), stats)

def _handle_query_params(metrics_list, all_entries):
    """Helper to process viz/log requests from the pre-fetched data."""
    action = st.query_params["action"]
    target_mid = st.query_params["mid"]
    all_df = pd.DataFrame(all_entries)
    
    if action == "viz":
        target_metric = next((m for m in metrics_list if str(m['id']) == target_mid), None)
        if target_metric:
            m_df = all_df[all_df['metric_id'] == target_mid]
            stats = visualize.get_metric_stats(m_df)
            st.query_params.clear()
            _show_advanced_viz_dialog(target_metric, m_df.to_dict('records'), stats)
    
    elif action == "log":
        st.session_state["last_active_mid"] = target_mid
        st.query_params.clear()
        st.rerun()

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
    High-density native row. Maintains your 1-row layout without the reload delay.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    with st.container(border=True):
        # Precise column ratios to keep everything in one row on mobile
        col_info, col_val, col_btns = st.columns([4, 2.5, 3.5], vertical_alignment="center")

        with col_info:
            st.markdown(f"<div style='line-height:1;'><span style='font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;'>{cat_name}</span><br><b style='font-size: 0.9rem;'>{m_name}</b></div>", unsafe_allow_html=True)

        with col_val:
            st.markdown(f"<div style='line-height:1;'><span style='font-size: 0.6rem; opacity: 0.7;'>LATEST</span><br><b style='font-size: 1.1rem; color: {trend_color};'>{val_display}</b></div>", unsafe_allow_html=True)

        with col_btns:
            # Sub-columns for buttons to sit side-by-side
            b1, b2 = st.columns(2)
            if b1.button("➕", key=f"log_{mid}", use_container_width=True):
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Record Data"
                st.rerun() # Switches tabs instantly as data is already cached

            if b2.button("📊", key=f"viz_{mid}", use_container_width=True):
                _show_advanced_viz_dialog(metric, entries, stats)