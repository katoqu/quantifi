import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize # Ensure your visualization module is imported

import streamlit as st
import models
import pandas as pd
import auth
from ui import visualize

def show_landing_page():
    """
    Simplified Mobile Dashboard with one-handed category navigation.
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
    
    # 1. SETUP CATEGORY NAVIGATION (One-Handed Pills)
    # Define options and ensure a persistent selection state
    cat_options = ["All"] + sorted([c['name'].title() for c in cats])
    
    if "active_cat_filter" not in st.session_state:
        st.session_state["active_cat_filter"] = "All"

    # Use st.pills as the lightweight alternative
    selected_cat = st.pills(
        "📁 Filter Categories",
        options=cat_options,
        selection_mode="single",
        default=st.session_state["active_cat_filter"],
        key="cat_filter_pill",
        label_visibility="collapsed"
    )
    
    # Sync choice to session state
    current_filter = selected_cat if selected_cat else "All"
    st.session_state["active_cat_filter"] = current_filter

    # 2. SORTING LOGIC (Recency-first)
    scored_metrics = []
    ts_min = pd.Timestamp.min.tz_localize('UTC') 

    for m in metrics_list:
        entries = models.get_entries(metric_id=m['id'])
        if entries:
            timestamps = pd.to_datetime([e['recorded_at'] for e in entries], format='mixed', utc=True)
            latest_ts = max(timestamps) 
        else:
            latest_ts = ts_min
        scored_metrics.append((latest_ts, m, entries))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)

    # 3. APPLY CATEGORY FILTER
    display_metrics = []
    for latest_ts, m, entries in scored_metrics:
        m_cat = cat_map.get(m.get('category_id'), "Uncat")
        if current_filter == "All" or m_cat == current_filter:
            display_metrics.append((latest_ts, m, entries))

    # 4. RENDER GRID
    if not display_metrics:
        st.info(f"No metrics found in the '{current_filter}' category.")
        return

    cols = st.columns(2)
    for i, (_, m, entries) in enumerate(display_metrics):
        with cols[i % 2]:
            _render_action_card(m, cat_map, entries)

@st.dialog("Advanced Analytics")
def _show_advanced_viz_dialog(metric, entries):
    """
    Detailed analytics overlay with statistical trends.
    """
    st.subheader(f"📈 {metric['name'].title()} Trends")
    
    if not entries:
        st.info("Record more data to see advanced trends.")
        return

    df = pd.DataFrame(entries)
    df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='mixed', utc=True)
    df = df.sort_values("recorded_at")

    # 1. Advanced Metrics: 7-Day Moving Average & Period Change
    c1, c2 = st.columns(2)
    
    if len(df) >= 7:
        ma7 = df['value'].rolling(window=7).mean().iloc[-1]
        diff = df['value'].iloc[-1] - ma7
        c1.metric("7D Avg", f"{ma7:.1f}", delta=f"{diff:.1f}", delta_color="inverse")
    
    if len(df) >= 2:
        last_val = df['value'].iloc[-1]
        prev_val = df['value'].iloc[-2]
        pct_change = ((last_val - prev_val) / prev_val) * 100
        c2.metric("Last Change", f"{last_val:.1f}", delta=f"{pct_change:.1f}%")

    st.divider()

    # 2. Reused Visualizations
    visualize.show_visualizations(df, metric.get('unit_name', ''), metric['name'])
    
    # 3. Direct Navigation
    if st.button("Go to Full History", use_container_width=True):
        st.session_state["last_active_mid"] = metric['id']
        st.query_params["metric_id"] = metric['id']
        st.rerun()

def _render_action_card(metric, cat_map, entries):
    """
    High-contrast card with dual actions: Log and Analyze.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    m_unit = metric.get('unit_name', '')
    
    latest_val = "—"
    last_date = ""

    if entries:
        df = pd.DataFrame(entries)
        df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='mixed', utc=True)
        latest_val = f"{df['value'].iloc[-1]:.1f}"
        last_date = df['recorded_at'].max().strftime('%d %b')

    with st.container(border=True):
        # Header with brand accent color
        st.markdown(f"""
            <div style="margin-bottom: -5px;">
                <span style="font-size: 0.6rem; color: #FF4B4B; font-weight: 700; text-transform: uppercase;">{cat_name}</span>
                <h4 style="margin: 0; font-size: 1.0rem; line-height: 1.2;">{m_name}</h4>
            </div>
        """, unsafe_allow_html=True)
        
        st.metric(label=last_date if last_date else "No Data", value=f"{latest_val} {m_unit}")
        
        # Action Row: Primary Log and Secondary Analytics
        btn_col, viz_col = st.columns([4, 1.2])
        with btn_col:
            if st.button("➕ Log", key=f"btn_{mid}", use_container_width=True, type="primary"):
                st.session_state["last_active_mid"] = mid
                st.query_params["metric_id"] = mid
                st.rerun()
        with viz_col:
            if st.button("📊", key=f"viz_{mid}", use_container_width=True):
                _show_advanced_viz_dialog(metric, entries)