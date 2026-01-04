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
        
    # USER GREETING
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
        # LOCAL FILTERING: No database call here anymore!
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
    
    # Inside _show_advanced_viz_dialog
    if st.button("Go to Full History", use_container_width=True):
        st.session_state["last_active_mid"] = metric['id']
        st.session_state["tracker_view_selector"] = "Edit Data" # Or your desired tab
        st.rerun()

def _render_action_card(metric, cat_map, entries, stats):
    """
    Ultra-Compact Pill-Action Row: Uses segmented control to force 
    a single-line layout and native performance.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")

    # Force horizontal layout for columns
    st.markdown("""
        <style>
            div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
            }
            div[data-testid="column"] { min-width: 0px !important; }
        </style>
    """, unsafe_allow_html=True)

def _render_action_card(metric, cat_map, entries, stats):
    """
    Locked Single-Row Card: Uses hard flex constraints to prevent 
    mobile stacking while ensuring vertical alignment.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    val_display = f"{stats['latest']:.1f}" if stats else "—"
    trend_color = "#28a745" if (stats.get('change') or 0) >= 0 else "#dc3545"

    # CRITICAL CSS: Forces the 'stHorizontalBlock' to never wrap
    st.markdown("""
        <style>
            /* Force horizontal layout even on small mobile screens */
            div[data-testid="stHorizontalBlock"] {
                display: flex !important;
                flex-direction: row !important;
                flex-wrap: nowrap !important;
                align-items: center !important;
                gap: 0.3rem !important; /* Tight spacing for mobile */
            }
            
            /* Remove the 16px minimum width that forces stacking */
            div[data-testid="column"] {
                min-width: 0px !important;
                flex: 1 1 auto !important;
            }

            /* Tighten the pill container specifically */
            div[data-testid="stPills"] {
                margin-top: 0px !important;
                width: fit-content !important;
            }
        </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # We use strict percentage-based columns
        # 40% Name | 25% Value | 35% Actions
        col_id, col_val, col_act = st.columns([4, 2.5, 3.5], vertical_alignment="center")

        with col_id:
            st.markdown(f"""
                <div style='line-height: 1.1; overflow: hidden;'>
                    <span style='font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;'>{cat_name}</span><br>
                    <b style='font-size: 0.85rem; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;'>{m_name}</b>
                </div>
            """, unsafe_allow_html=True)

        with col_val:
            st.markdown(f"""
                <div style='line-height: 1.0; border-left: 1.5px solid rgba(128,128,128,0.2); padding-left: 8px;'>
                    <span style='font-size: 0.55rem; opacity: 0.7; font-weight: 600;'>LATEST</span><br>
                    <b style='font-size: 1.05rem; color: {trend_color};'>{val_display}</b>
                </div>
            """, unsafe_allow_html=True)

        with col_act:
            # Piling the actions into a segmented control/pills for a locked-row look
            choice = st.pills(
                label=f"actions_{mid}",
                options=["➕", "📊"],
                key=f"pills_{mid}",
                label_visibility="collapsed",
                selection_mode="single"
            )

            if choice == "➕":
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Record Data"
                st.rerun() # Instant fragment rerun
            elif choice == "📊":
                _show_advanced_viz_dialog(metric, entries, stats)