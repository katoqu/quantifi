import streamlit as st
import pandas as pd
import auth
import models
from ui import visualize, pages

def show_landing_page(metrics_list, all_entries):
    cats = models.get_categories() or []
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    
    if not metrics_list:
        st.info("No metrics found. Let's start tracking!")
        if st.button("✨ Create Your First Metric", use_container_width=True, type="primary"):
            st.session_state["tracker_view_selector"] = "Manage Metrics"
            st.rerun()
        return
    render_metric_grid(metrics_list, cats, all_entries)

@st.fragment
def render_metric_grid(metrics_list, cats, all_entries):
    #Initialize the session state for the pills if it doesn't exist
    if "cat_filter" not in st.session_state:
        st.session_state["cat_filter"] = "All"

    cat_map = {c['id']: c['name'].title() for c in cats}
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    
    st.pills("Filter", options=cat_options, key="cat_filter", label_visibility="collapsed")
    current_filter = st.session_state.get("cat_filter", "All")

    all_df = pd.DataFrame(all_entries)
    scored_metrics = []
    for m in metrics_list:
        m_df = all_df[all_df['metric_id'] == m['id']] if not all_df.empty else pd.DataFrame()
        stats = visualize.get_metric_stats(m_df)
        
        latest_ts = pd.Timestamp.min.tz_localize('UTC')
        if not m_df.empty:
            latest_ts = pd.to_datetime(m_df['recorded_at'], format='mixed', utc=True).max()
        scored_metrics.append((latest_ts, m, stats, m_df))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)
    
    for _, m, stats, m_df in scored_metrics:
        if current_filter == "All" or cat_map.get(m.get('category_id')) == current_filter:
            _render_action_card(m, cat_map, m_df.to_dict('records'), stats)

def _render_action_card(metric, cat_map, entries, stats):
    mid, m_name = metric['id'], metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    description = metric.get("description", "")
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    with st.container(border=True):
        col_main = st.columns([1])[0] 

        with col_main:
            st.markdown(f"""
                        <div class="action-card-grid">
                            <div class="metric-identity">
                                <span style="font-size: 0.65rem; color: #FF4B4B; font-weight: 700;">{cat_name.upper()}</span><br>
                                <div class="truncate-text" style="font-size: 0.95rem; font-weight: 800;">
                                    {m_name}
                                </div>
                            </div>
                            <div class="value-box">
                                <span style="font-size: 0.55rem; opacity: 0.7; font-weight: 600;">LATEST</span><br>
                                <b style="font-size: 1.1rem; color: {trend_color};">{val_display}</b>
                            </div>
                            <div></div> 
                        </div>
                        <div style="height: 15px;"></div> 
                    """, unsafe_allow_html=True)
            choice = st.pills(f"act_{mid}", options=["➕", "📊", "⚙️"], 
                              key=f"p_{mid}", 
                              label_visibility="collapsed",
                              help=description)
            
            if choice == "➕":
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Record"
                st.rerun()
            elif choice == "📊":
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Analytics"
                st.rerun()
            elif choice == "⚙️":
                # 1. Set the metric focus and tab selection
                st.session_state["last_active_mid"] = mid
                st.session_state["config_tab_selection"] = "📊 Edit Metric"
                
                # 2. Find the "Configure" page object from the navigation list
                nav_pages = st.session_state.get("nav_pages", [])
                config_page = next((p for p in nav_pages if p.title == "Configure"), None)
                
                if config_page:
                    st.switch_page(config_page)
                    st.rerun()
                else:
                    # Fallback if page object isn't found
                    st.error("Configure page not found in navigation.")

def show_advanced_analytics_view(metric):
    st.markdown(f"#### {metric['name'].title()} Trends")
    
    # 1. Fetch entries specifically for this metric using the function in models.py
    entries = models.get_entries(metric_id=metric['id']) #

    if not entries:
        # REPLACE st.info with a Button + Trigger
        st.info("Record more data to see advanced trends.")
        if st.button("➕ Record First Entry", type="primary", use_container_width=True):
            st.session_state["nav_to_record_trigger"] = True
            st.rerun()
        return

    # 2. Calculate stats and render visualizations
    df = pd.DataFrame(entries)
    stats = visualize.get_metric_stats(df)
    visualize.render_stat_row(stats, mode="advanced")
    st.divider()
    
    visualize.show_visualizations(df, metric.get('unit_name', ''), metric['name'])