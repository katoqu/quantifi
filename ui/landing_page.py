import streamlit as st
import models
import pandas as pd
import auth

def show_landing_page():
    """
    Ultra-dense mobile dashboard with perfectly equal spacing using Flexbox.
    Sorted by most recently updated metric.
    """
    # 1. Personalize welcome message
    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    st.title(f"🚀 Welcome back, {user_display}")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Head over to Settings to get started!")
        return

    cats = models.get_categories() or []
    cat_map = {c['id']: c['name'].title() for c in cats}
    
    # 2. Sorting Logic: Most Recent First
    scored_metrics = []
    for m in metrics_list:
        entries = models.get_entries(metric_id=m['id'])
        latest_ts = pd.to_datetime(max([e['recorded_at'] for e in entries])) if entries else pd.Timestamp.min
        scored_metrics.append((latest_ts, m, entries))
    
    scored_metrics.sort(key=lambda x: x[0], reverse=True)

    # 3. Render Dashboard Rows
    for _, m, entries in scored_metrics:
        _render_balanced_row(m, cat_map, entries)

def _render_balanced_row(metric, cat_map, entries):
    """
    Renders a single dashboard row with equal spacing between four key modules.
    """
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    
    with st.container(border=True):
        # We use st.columns with equal weights [1, 1, 1, 1] to force equal distribution
        # even on the narrowest mobile screens.
        cols = st.columns([1, 1, 1, 1], gap="small")
        
        # Module 1: Metadata
        with cols[0]:
            st.markdown(f"**{m_name}**<br><span style='font-size: 0.65rem; opacity: 0.7;'>📁 {cat_name}</span>", unsafe_allow_html=True)

        # Module 2: Trendline
        with cols[1]:
            if entries and len(entries) > 1:
                df = pd.DataFrame(entries)
                df['recorded_at'] = pd.to_datetime(df['recorded_at'])
                spark_data = df.sort_values("recorded_at").tail(7).set_index('recorded_at')['value']
                # Height 80 ensures visibility on mobile
                st.line_chart(spark_data, height=80, use_container_width=True)
            else:
                st.write("") 

        # Module 3: KPIs
        with cols[2]:
            if entries:
                df = pd.DataFrame(entries)
                latest_val = df["value"].iloc[-1]
                avg_val = df["value"].mean()
                
                # Formatted to 1 decimal digit
                st.markdown(f"""
                    <div style="display: flex; flex-direction: column; justify-content: center; align-items: center; 
                                background: var(--secondary-background-color); border-radius: 4px; padding: 4px; 
                                border: 1px solid var(--border-color); height: 80px;">
                        <div style="text-align: center; margin-bottom: 4px;">
                            <div style="font-size: 0.5rem; opacity: 0.7; text-transform: uppercase;">Latest</div>
                            <div style="font-size: 0.8rem; font-weight: bold;">{latest_val:.1f}</div>
                        </div>
                        <div style="width: 80%; height: 1px; background: var(--border-color); margin: 2px 0;"></div>
                        <div style="text-align: center;">
                            <div style="font-size: 0.5rem; opacity: 0.7; text-transform: uppercase;">Avg</div>
                            <div style="font-size: 0.8rem; font-weight: bold;">{avg_val:.1f}</div>
                        </div>
                    </div>
                """, unsafe_allow_html=True)

        # Module 4: Record Action
        with cols[3]:
            # Spacer to center the button vertically relative to the 80px chart
            st.markdown("<div style='height: 20px;'></div>", unsafe_allow_html=True)
            if st.button("➕", key=f"rec_{mid}", use_container_width=True):
                st.query_params["metric_id"] = mid
                st.rerun()