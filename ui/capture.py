import streamlit as st
import models
import utils
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from ui import visualize
from logic import editor_handler

@st.fragment
def show_tracker_suite(selected_metric):

    # 1. Capture Form
    show_capture(selected_metric)
    
    st.divider()

    # 2. Local Data Fetch (Only within fragment scope)
    dfe, m_unit, m_name = utils.collect_data(selected_metric)

    # 3. Inline Visualization Update
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(dfe, m_unit, m_name, show_pills=True)
    else:
        st.info("No data recorded for this metric yet. Add your first entry above.")

def _get_initial_datetime(mid):
    date_key = f"capture_date_{mid}"
    time_key = f"capture_time_{mid}"
    if date_key not in st.session_state:
        st.session_state[date_key] = dt.date.today()
    if time_key not in st.session_state:
        st.session_state[time_key] = dt.datetime.now().time().replace(second=0, microsecond=0)

def _get_value_input(utype, unit_name, smart_default, selected_metric, recent_values):
    if utype == "integer_range":
        rs = int(selected_metric.get("range_start", 0))
        re = int(selected_metric.get("range_end", 10))
        default_val = int(smart_default)
        if default_val < rs:
            default_val = rs
        elif default_val > re:
            default_val = re
        return st.slider(
            f"Value ({unit_name})",
            min_value=rs,
            max_value=re,
            value=default_val,
            step=1,
        )
    if utype == "integer":
        return st.number_input(f"Value ({unit_name})", value=int(smart_default), step=1, format="%d")
    step, fmt = _infer_float_step_and_format_from_history(recent_values)
    if step is None:
        step, fmt = _infer_float_step_and_format(smart_default)
    return st.number_input(f"Value ({unit_name})", value=float(smart_default), format=fmt, step=step)

def _infer_float_step_and_format(value, default_decimals=1, max_decimals=6):
    try:
        dec = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return 1.0, f"%.{default_decimals}f"
    decimals = max(0, -dec.as_tuple().exponent)
    decimals = min(max_decimals, decimals)
    if decimals == 0:
        return 1.0, "%.0f"
    step = 10 ** (-decimals)
    return step, f"%.{decimals}f"

def _infer_float_step_and_format_from_history(values, default_decimals=1, max_decimals=6):
    if not values or len(values) < 2:
        return None, None
    deltas = [abs(curr - prev) for prev, curr in zip(values, values[1:])]
    avg_delta = sum(deltas) / len(deltas) if deltas else 0
    if avg_delta <= 0:
        return None, None
    decimals = _max_decimals(values, default_decimals, max_decimals)
    step = _round_down(avg_delta / 5, decimals)
    if step <= 0:
        step = 10 ** (-decimals)
    return step, f"%.{decimals}f"

def _max_decimals(values, default_decimals, max_decimals):
    decimals = default_decimals
    for value in values:
        try:
            dec = Decimal(str(value))
        except (InvalidOperation, ValueError):
            continue
        decimals = max(decimals, max(0, -dec.as_tuple().exponent))
    return min(max_decimals, decimals)

def _round_down(value, decimals):
    if decimals <= 0:
        return float(Decimal(str(value)).quantize(Decimal("1"), rounding=ROUND_DOWN))
    quant = Decimal(f"1e-{decimals}")
    return float(Decimal(str(value)).quantize(quant, rounding=ROUND_DOWN))

def _get_recent_values(metric_id, limit=5):
    entries = models.get_entries(metric_id)
    if not entries:
        return []
    entries = sorted(entries, key=lambda row: row.get("recorded_at", ""))
    values = []
    for row in entries[-limit:]:
        try:
            values.append(float(row["value"]))
        except (TypeError, ValueError):
            continue
    return values

def show_capture(selected_metric):
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    utype = selected_metric.get("unit_type", "float")
    
    # Fetch smart default once per fragment execution
    last_entry = models.get_latest_entry_only(mid)
    recent_values = _get_recent_values(mid) if utype not in ("integer", "integer_range") else []
    fallback = selected_metric.get("range_start", 0.0)
    smart_default = last_entry['value'] if last_entry else float(fallback if fallback is not None else 0.0)

    with st.container(border=True):
        if selected_metric.get("description"):
            st.caption(selected_metric["description"])

        _get_initial_datetime(mid)
        
        # --- FIX: Toggle is now OUTSIDE the form ---
        # This allows it to trigger a rerun so the form can "react" to it.
        show_time_toggle = st.toggle("Set specific time", value=False, key=f"toggle_time_{mid}")
        
        with st.form(f"capture_entry_submit_{mid}", border=False):
            date_input = st.date_input("📅 Date", key=f"capture_date_{mid}")
            
            if show_time_toggle:
                # This will now appear instantly when the toggle is clicked
                time_input = st.time_input(
                    "⏰ Time",
                    step=60,
                    key=f"capture_time_{mid}",
                )
            else:
                # Fallback to current/stored time if hidden
                time_input = st.session_state[f"capture_time_{mid}"]

            val = _get_value_input(utype, unit_name, smart_default, selected_metric, recent_values)

            submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
            
            if submitted:
                final_dt = dt.datetime.combine(date_input, time_input)
                models.create_entry({
                    "metric_id": mid, 
                    "value": val, 
                    "recorded_at": final_dt.isoformat()
                })
                
                # Clear the editor's draft so it fetches the new entry on next render
                editor_handler.reset_editor_state(f"data_{mid}", mid)

                if hasattr(models.get_latest_entry_only, "clear"):
                    models.get_latest_entry_only.clear()
                utils.finalize_action(f"Saved: {val} {unit_name}")

                st.rerun(scope="fragment")