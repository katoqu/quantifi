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
    if not all_df.empty:
        all_df['recorded_at'] = pd.to_datetime(all_df['recorded_at'], format='mixed', utc=True)
        latest_by_metric = all_df.groupby('metric_id')['recorded_at'].max()
        grouped_by_metric = {mid: df for mid, df in all_df.groupby('metric_id')}
    else:
        latest_by_metric = pd.Series(dtype='datetime64[ns, UTC]')
        grouped_by_metric = {}

    scored_metrics = []
    for m in metrics_list:
        m_df = grouped_by_metric.get(m['id'], pd.DataFrame())
        stats = visualize.get_metric_stats(m_df) if not m_df.empty else {}
        if not m_df.empty:
            spark_values = list(m_df.sort_values("recorded_at")["value"].tail(12))
        else:
            spark_values = []
        stats["spark_values"] = spark_values
        latest_ts = latest_by_metric.get(m['id'], pd.Timestamp.min.tz_localize('UTC'))
        scored_metrics.append((latest_ts, m, stats))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)
    
    for _, m, stats in scored_metrics:
        if current_filter == "All" or cat_map.get(m.get('category_id')) == current_filter:
            _render_action_card(m, cat_map, stats)

def _render_action_card(metric, cat_map, stats):
    mid, m_name = metric['id'], metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    description = metric.get("description", "")
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    with st.container(border=True):
        col_main = st.columns([1])[0] 

        with col_main:
            sparkline_html = _render_sparkline(stats.get("spark_values", []), trend_color)
            card_html = "\n".join([
                '<div class="action-card-grid">',
                '  <div class="metric-identity">',
                f'    <span style="font-size: 0.65rem; color: #FF4B4B; font-weight: 700;">{cat_name.upper()}</span><br>',
                f'    <div class="truncate-text" style="font-size: 0.95rem; font-weight: 800;">{m_name}</div>',
                '  </div>',
                '  <div class="value-box">',
                '    <span style="font-size: 0.55rem; opacity: 0.7; font-weight: 600;">TREND</span><br>',
                f'    <div style="height: 28px; display: flex; align-items: center;">{sparkline_html}</div>',
                '  </div>',
                '  <div></div>',
                '</div>',
                '<div style="height: 15px;"></div>'
            ])
            st.markdown(card_html, unsafe_allow_html=True)
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

def _render_sparkline(values, color):
    if not values:
        return '<span style="font-size: 0.9rem; opacity: 0.6;">—</span>'

    width = 96
    height = 28
    pad = 2
    vmin = min(values)
    vmax = max(values)

    if len(values) == 1 or vmax == vmin:
        points = f"{pad},{height/2} {width-pad},{height/2}"
    else:
        step = (width - pad * 2) / (len(values) - 1)
        span = vmax - vmin
        pts = []
        for i, v in enumerate(values):
            x = pad + i * step
            y = height - pad - ((v - vmin) / span) * (height - pad * 2)
            pts.append(f"{x:.2f},{y:.2f}")
        points = " ".join(pts)

    return (
        f'<svg viewBox="0 0 {width} {height}" width="100%" height="{height}" '
        f'preserveAspectRatio="none" aria-hidden="true">'
        f'<polyline fill="none" stroke="{color}" stroke-width="2" points="{points}" '
        f'stroke-linecap="round" stroke-linejoin="round"/></svg>'
    )

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

    # 2. Render visualizations
    df = pd.DataFrame(entries)
    visualize.show_visualizations(df, metric.get('unit_name', ''), metric['name'])
