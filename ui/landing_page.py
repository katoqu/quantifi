import streamlit as st
import models
import pandas as pd

def show_landing_page():
    st.title("🚀 Welcome back, QuantifI")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Head over to Settings to get started!")
        return

    cats = models.get_categories() or []
    cat_map = {c['id']: c['name'].title() for c in cats}
    
    # Create the Grid
    cols = st.columns(3)
    for i, m in enumerate(metrics_list):
        with cols[i % 3]:
            _render_summary_card(m, cat_map)

def _render_summary_card(metric, cat_map):
    mid = metric['id']
    m_name = metric['name'].title()
    m_unit = metric.get('unit_name', '')
    cat_name = cat_map.get(metric.get('category_id'), "Uncategorized")
    
    entries = models.get_entries(metric_id=mid)
    
    with st.container(border=True):
        st.caption(f"📁 {cat_name}")
        st.subheader(m_name)
        
        if entries:
            df = pd.DataFrame(entries).sort_values("recorded_at")
            latest = df.iloc[-1]
            st.metric(label="Current", value=f"{latest['value']:g} {m_unit}")
            
            if len(df) > 1:
                spark_data = df.tail(7).copy()
                spark_data['Date'] = pd.to_datetime(spark_data['recorded_at']).dt.strftime('%b %d')
                spark_data = spark_data.set_index('Date')['value']
                st.line_chart(spark_data, height=80, use_container_width=True)
        else:
            st.info("No data yet.")

        # THE LINK LOGIC:
        # Instead of a form, we set a query param and change the view mode
        if st.button(f"➕ Record {m_name}", key=f"rec_{mid}", use_container_width=True):
            st.query_params["metric_id"] = mid
            st.rerun()