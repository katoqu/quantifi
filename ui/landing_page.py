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

    with st.container(border=True):
        # 75/25 split ensures the name has plenty of room
        col_info, col_actions = st.columns([7, 3], vertical_alignment="center")

        with col_info:
            st.markdown(
                f"<div style='line-height:1.1;'>"
                f"<span style='font-size:0.6rem; color:#FF4B4B; font-weight:700;'>{cat_name.upper()}</span><br>"
                f"<span style='font-size:0.9rem; font-weight:600;'>{m_name}</span>"
                f"</div>", 
                unsafe_allow_html=True
            )

        with col_actions:
            # Using segmented_control for a compact, single-row action menu
            choice = st.segmented_control(
                label=f"Actions for {mid}",
                options=["➕", "📊"],
                key=f"actions_{mid}",
                label_visibility="collapsed",
                selection_mode="single"
            )

            # Trigger logic immediately upon selection
            if choice == "➕":
                st.session_state["last_active_mid"] = mid
                st.session_state["tracker_view_selector"] = "Record Data"
                st.rerun()
            elif choice == "📊":
                _show_advanced_viz_dialog(metric, entries, stats)