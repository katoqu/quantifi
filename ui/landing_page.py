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
    """
    Optimized 2-column internal layout:
    Left: Identity (Category + Name)
    Right: Data & Actions (Latest Value + Buttons)
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    
    with st.container(border=True):
        # Create the main internal split
        col_id, col_data = st.columns([1.5, 1])
        
        with col_id:
            # IDENTITY: Category and Name
            st.markdown(f"""
                <div style="margin-top: 5px;">
                    <span style="font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;">{cat_name}</span>
                    <h4 style="margin: 0; font-size: 0.95rem; line-height: 1.1; word-wrap: break-word;">
                        {m_name}
                    </h4>
                </div>
            """, unsafe_allow_html=True)
            
        with col_data:
            # DATA: Latest Value
            if stats:
                # We use a custom display here instead of render_stat_row 
                # to fit the value tightly in this specific column
                st.markdown(f"""
                    <div style="text-align: right;">
                        <span style="font-size: 0.7rem; opacity: 0.7;">{stats['last_date']}</span>
                        <div style="font-size: 1.2rem; font-weight: bold; margin-top: -5px;">
                            {stats['latest']:.1f}
                        </div>
                    </div>
                """, unsafe_allow_html=True)
            else:
                st.markdown("<div style='text-align: right; opacity: 0.5;'>—</div>", unsafe_allow_html=True)

        # ACTION ROW: Standard buttons below the split
        btn_col, viz_col = st.columns([3, 1])
        with btn_col:
            if st.button("➕ Log", key=f"btn_{mid}", use_container_width=True, type="primary"):
                st.session_state["last_active_mid"] = mid
                st.query_params["metric_id"] = mid
                st.rerun()
        with viz_col:
            if st.button("📊", key=f"viz_{mid}", use_container_width=True):
                _show_advanced_viz_dialog(metric, entries, stats)