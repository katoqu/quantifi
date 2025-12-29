import streamlit as st
from ui import manage_lookups, capture, visualize, metrics
import pandas as pd
import models
import utils
import auth
from datetime import timedelta
from data_editor import editable_metric_table

# 1. Initialize State
auth.init_session_state()
if "show_debug_panel" not in st.session_state:
    st.session_state.show_debug_panel = False

def show_debug_logs():
    # Only show if the user toggled it on
    if st.session_state.show_debug_panel:
        with st.expander("🛠 Auth Debug Logs (Newest First)", expanded=True):
            if not st.session_state.get("auth_debug"):
                st.info("No logs captured yet.")
            else:
                for log in reversed(st.session_state.auth_debug):
                    st.text(log)
                if st.button("Clear History"):
                    st.session_state.auth_debug = []
                    st.rerun()

# 2. Sidebar Toggle (Always visible)
#with st.sidebar:
#    st.title("Admin")
#    if st.button("Toggle Debug View"):
#        st.session_state.show_debug_panel = not st.session_state.show_debug_panel
#        st.rerun()

# 3. Execution Order
show_debug_logs() # Show logs at the very top if enabled

# 3. If not authenticated, show auth page
if not auth.is_authenticated():
    auth.auth_page()
    st.stop()

# 4. Sidebar Logout Logic
# This stays visible on both "Tracker" and "Configure" pages
with st.sidebar:
    st.write(f"Logged in as: **{auth.get_current_user().email}**")
    if st.button("Log Out", use_container_width=True):
        auth.sign_out()

def main_dashboard():
    st.title("QuantifI - Dashboard")

    # select metric and capture data
    metrics = models.get_metrics() or []
    if not metrics:
        st.info("No metrics defined yet. Create one in 'Define & configure'.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    metric_idx = st.selectbox("Metric to capture", options=list(range(len(metrics))), format_func=lambda i: utils.format_metric_label(metrics[i], unit_meta))
    selected_metric = metrics[metric_idx]

    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)

    # Show capture section
    capture.show_capture(selected_metric, unit_meta)

    # Collect data for visualization and show plot
    visualize.show_visualizations(dfe, m_unit, m_name )

def settings_page():
    st.title("Settings")
    
    # Get data for selection
    cats = models.get_categories()
    units = models.get_units()
    
    # Manage lookups (categories and units)
    manage_lookups.show_manage_lookups()
    
    # Create metrics
    metrics.show_create_metric(cats, units)


def edit_data_page():
    st.title("Manage & Edit Data")
    
    # 1. Fetch metadata and metrics
    metrics_list = models.get_metrics() or []
    if not metrics_list:
        st.info("No metrics defined yet.")
        return

    units = models.get_units() or []
    unit_meta = {u["id"]: u for u in units}

    # 2. Metric Selection
    metric_idx = st.selectbox(
        "Select metric to manage", 
        options=list(range(len(metrics_list))), 
        format_func=lambda i: utils.format_metric_label(metrics_list[i], unit_meta),
        key="edit_page_metric_select"
    )
    selected_metric = metrics_list[metric_idx]
    mid = selected_metric.get("id")
    
    # --- Unsaved Changes Detection Logic ---
    state_key = f"data_{mid}"
    has_unsaved_changes = False
    if state_key in st.session_state:
        df_draft = st.session_state[state_key]
        has_unsaved_changes = (df_draft["Change Log"] != "").any()

    # 3. Collect FULL Dataset
    dfe, m_unit, m_name = utils.collect_data(selected_metric, unit_meta)

    if dfe is not None and not dfe.empty:
        dfe['recorded_at'] = pd.to_datetime(dfe['recorded_at'])
        abs_min = dfe['recorded_at'].min().date()
        abs_max = dfe['recorded_at'].max().date()

        st.subheader("🗓️ Filter Management Window")
        
        # 1. Setup Keys for this specific metric
        date_picker_key = f"date_range_{mid}"
        prev_date_key = f"prev_date_{mid}"

        # 2. Initialize tracking state if first run
        if prev_date_key not in st.session_state:
            st.session_state[prev_date_key] = (abs_min, abs_max)
        
        # 3. Handle the "Revert" or "Accept" logic BEFORE the widget is rendered
        # We look at the value currently in session state from the PREVIOUS interaction
        if date_picker_key in st.session_state:
            current_ui_val = st.session_state[date_picker_key]
            
            # Conflict Check: UI changed, but we have unsaved work
            if current_ui_val != st.session_state[prev_date_key] and has_unsaved_changes:
                st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard your current edits.")
                
                c1, c2 = st.columns(2)
                if c1.button("Discard Changes & Update Range", use_container_width=True):
                    # Accept the new date, clear the draft, update tracker
                    del st.session_state[state_key]
                    st.session_state[prev_date_key] = current_ui_val
                    st.rerun()
                
                if c2.button("Keep Editing (Revert Date)", type="primary", use_container_width=True):
                    # SUCCESS: We can modify this key because st.date_input hasn't run yet in THIS execution
                    st.session_state[date_picker_key] = st.session_state[prev_date_key]
                    st.rerun()
                
                st.stop() # Prevent the rest of the page from loading while warning is active
            else:
                # No conflict: Update our tracker for next time
                st.session_state[prev_date_key] = current_ui_val

        # 4. Initialize the widget key if it's the very first load for this metric
        if date_picker_key not in st.session_state:
            st.session_state[date_picker_key] = st.session_state[prev_date_key]

        # 5. Render the Widget (Binds to the key we just potentially reverted)
        col1, col2 = st.columns([2, 1])
        with col1:
            current_date_range = st.date_input(
                "Select range (Click start date, then end date)",
                key=date_picker_key,
                min_value=abs_min,
                max_value=abs_max + timedelta(days=365) 
            )

        # --- Revert Logic Fix ---
        # If the user changed the date but has unsaved work
        if current_date_range != st.session_state[prev_date_key] and has_unsaved_changes:
            st.warning("⚠️ **Unsaved Changes Detected!** Changing the date range will discard your current edits.")
            
            c1, c2 = st.columns(2)
            if c1.button("Discard Changes & Update Range", use_container_width=True):
                # Accept the new date, clear the draft
                del st.session_state[state_key]
                st.session_state[prev_date_key] = current_date_range
                st.rerun()
            
            if c2.button("Keep Editing (Revert Date)", type="primary", use_container_width=True):
                # FORCE the widget to go back to the previous value by overwriting its state key
                st.session_state[date_picker_key] = st.session_state[prev_date_key]
                st.rerun()
            
            st.stop()
        else:
            # No conflict: Update the "previous" tracker to match current UI
            st.session_state[prev_date_key] = current_date_range

        # 5. Filter Execution Logic
        if isinstance(current_date_range, tuple) and len(current_date_range) == 2:
            start_date, end_date = current_date_range
            mask = (dfe['recorded_at'].dt.date >= start_date) & (dfe['recorded_at'].dt.date <= end_date)
            filtered_df = dfe.loc[mask].sort_values("recorded_at", ascending=False)

            visualize.show_visualizations(filtered_df, m_unit, m_name)
            
            st.divider()

            st.write("### ✏️ Edit Records")
            st.caption(f"Showing {len(filtered_df)} entries found between {start_date} and {end_date}")
            
            visualize.editable_metric_table(filtered_df, m_unit, mid)
        else:
            st.info("Please select both a start and end date on the calendar to see records.")
    else:
        st.info("No data recorded for this metric yet.")


# Update the Navigation
pg = st.navigation([
    st.Page(main_dashboard, title="Tracker", icon="📊"),
    st.Page(edit_data_page, title="Edit Data", icon="✏️"), # New Page
    st.Page(settings_page, title="Configure", icon="⚙️"),
])

pg.run()