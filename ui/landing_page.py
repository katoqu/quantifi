import streamlit as st
import models
import pandas as pd
import auth

def show_landing_page():
    """
    Ultra-dense mobile dashboard. 
    Forces columns to sit tight against each other with zero unnecessary gaps.
    """
    # 1. Inject CSS for tight horizontal alignment
    st.markdown("""
        <style>
        [data-testid="stHorizontalBlock"] {
            flex-wrap: nowrap !important;
            gap: 0.3rem !important;
            justify-content: flex-start !important;
            align-items: center !important;
        }
        [data-testid="column"] {
            min-width: 0px !important;
            flex-shrink: 1 !important;
            width: auto !important;
        }
        [data-testid="stHorizontalBlock"] > div:first-child {
            padding-left: 0px !important;
            padding-right: 0px !important;
            flex: 0 1 auto !important;
        }
        [data-testid="stHorizontalBlock"] > div:last-child {
            padding-right: 4px !important;
            padding-left: 2px !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] > div {
            padding: 0.3rem !important;
        }
        </style>
    """, unsafe_allow_html=True)

    user = auth.get_current_user()
    user_display = user.email.split('@')[0].capitalize() if user else "User"
    st.title(f"🚀 Welcome, {user_display}")
    
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics found. Head to Settings to get started.")
        return

    cats = models.get_categories() or []
    cat_map = {c['id']: c['name'].title() for c in cats}
    
    # 3. Sorting Logic: Fixed Timezone comparison
    scored_metrics = []
    # Create a timezone-aware floor for comparison
    ts_min = pd.Timestamp.min.tz_localize('UTC') 

    for m in metrics_list:
        entries = models.get_entries(metric_id=m['id'])
        if entries:
            # Convert to datetime and ensure UTC awareness for the max calculation
            timestamps = pd.to_datetime([e['recorded_at'] for e in entries], format='ISO8601', utc=True)
            latest_ts = max(timestamps) 
        else:
            latest_ts = ts_min
            
        scored_metrics.append((latest_ts, m, entries))
    
    # Now both latest_ts and ts_min are UTC-aware, so sorting works
    scored_metrics.sort(key=lambda x: x[0], reverse=True)

    for _, m, entries in scored_metrics:
        _render_true_single_row(m, cat_map, entries)

def _render_true_single_row(metric, cat_map, entries):
    mid = metric['id']
    m_name = metric['name'].title()
    cat_name = cat_map.get(metric.get('category_id'), "Uncat")
    
    count = len(entries)
    last_date = "—"
    latest_val = 0.0
    avg_val = 0.0

    if count > 0:
        df = pd.DataFrame(entries)
        # Ensure UTC and localize to local or generic format for display
        df['recorded_at'] = pd.to_datetime(df['recorded_at'], format='ISO8601', utc=True)
        last_date = df['recorded_at'].max().strftime('%d/%m')
        latest_val = df["value"].iloc[-1]
        avg_val = df["value"].mean()

    with st.container(border=True):
        cols = st.columns([0.8, 3.5, 0.4])
        
        with cols[0]:
            st.markdown(f"""
                <div style="line-height: 1; min-width: 60px;">
                    <b style="font-size: 0.75rem;">{m_name}</b><br>
                    <span style="font-size: 0.5rem; opacity: 0.7;">📁 {cat_name}</span>
                </div>
            """, unsafe_allow_html=True)

        with cols[1]:
            st.markdown(f"""
                <div style="display: flex; justify-content: space-between; align-items: center; 
                            background: var(--secondary-background-color); border-radius: 6px; 
                            padding: 4px; border: 1px solid var(--border-color); height: 36px; width: 100%;">
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.4rem; opacity: 0.6;">Latest</div>
                        <div style="font-size: 0.7rem; font-weight: bold;">{latest_val:.1f}</div>
                    </div>
                    <div style="width: 1px; height: 12px; background: var(--border-color);"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.4rem; opacity: 0.6;">Avg</div>
                        <div style="font-size: 0.7rem; font-weight: bold;">{avg_val:.1f}</div>
                    </div>
                    <div style="width: 1px; height: 12px; background: var(--border-color);"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.4rem; opacity: 0.6;">Entries</div>
                        <div style="font-size: 0.7rem; font-weight: bold;">{count}</div>
                    </div>
                    <div style="width: 1px; height: 12px; background: var(--border-color);"></div>
                    <div style="text-align: center; flex: 1;">
                        <div style="font-size: 0.4rem; opacity: 0.6;">Last entry</div>
                        <div style="font-size: 0.65rem; font-weight: bold;">{last_date}</div>
                    </div>
                </div>
            """, unsafe_allow_html=True)

        with cols[2]:
            if st.button("➕", key=f"rec_{mid}", use_container_width=True):
                st.query_params["metric_id"] = mid
                st.rerun()