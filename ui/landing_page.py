import streamlit as st
import pandas as pd
import auth
import models
from ui import visualize

def show_landing_page(metrics_list, all_entries):
    cats = models.get_categories() or []
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    
    st.markdown(f"### 🚀 Welcome, {user_display}")

    if not metrics_list:
        st.info("No metrics found. Let's start tracking!")
        if st.button("✨ Create Your First Metric", use_container_width=True, type="primary"):
            st.session_state["tracker_view_selector"] = "Manage Metrics"
            st.rerun()
        return

    render_metric_grid(metrics_list, cats, all_entries)

@st.fragment
def render_metric_grid(metrics_list, cats, all_entries):
    cat_map = {c['id']: c['name'].title() for c in cats}
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    
    st.pills("Filter", options=cat_options, key="cat_filter", label_visibility="collapsed")
    current_filter = st.session_state.get("cat_filter", "All")

    # REFINED CSS: Added vertical spacing for pills and grid padding
    st.markdown("""
    <style>
            /* 1. SHRINK THE CONTAINER BOX: Targets the inner padding of the border */
            [data-testid="stVerticalBlockBorderWrapper"] > div {
                padding: 4px 10px !important; 
            }

            /* 2. THE 50/50 GRID: Split the flex space equally, lock buttons to 100px */
            .action-card-grid {
                display: grid !important;
                grid-template-columns: 2fr 1fr 100px !important; 
                align-items: center !important;
                width: 100%;
                gap: 0px !important;
            }

            /* 3. TIGHTEN TEXT: Reduce vertical space between lines */
            .metric-identity {
                line-height: 1.0 !important;
                min-width: 0;
            }

            .value-box {
                justify-self: start; 
                border-left: 1px solid rgba(128,128,128,0.2); 
                padding-left: 10px;
                line-height: 1.0;
                text-align: left;
            }

            div[data-testid="stPills"] { 
                margin-top: 8px !important; 
                display: flex;
                justify-content: flex-end;
            }
        </style>
    """, unsafe_allow_html=True)

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
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    with st.container(border=True):
        col_main = st.columns([1])[0] 
        
        with col_main:
            st.markdown(f"""
                <div class="action-card-grid">
                    <div style="line-height: 1.2; min-width: 0;">
                        <span style="font-size: 0.65rem; color: #FF4B4B; font-weight: 700;">{cat_name.upper()}</span><br>
                        <div class="truncate-text" style="font-size: 0.95rem; font-weight: 800;">{m_name}</div>
                    </div>
                    <div class="value-box">
                        <span style="font-size: 0.55rem; opacity: 0.7; font-weight: 600;">LATEST</span><br>
                        <b style="font-size: 1.1rem; color: {trend_color};">{val_display}</b>
                    </div>
                    <div></div> </div>
            """, unsafe_allow_html=True)

            choice = st.pills(f"act_{mid}", options=["➕", "📊"], key=f"p_{mid}", label_visibility="collapsed")
            
            if choice == "➕":
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Record Data"
                st.rerun()
            elif choice == "📊":
                _show_advanced_viz_dialog(metric, entries, stats)

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
    
    if st.button("Edit History", use_container_width=True):
        st.session_state["last_active_mid"] = metric['id']
        st.session_state["tracker_view_selector"] = "Edit Data"
        st.rerun()