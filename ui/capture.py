import pandas as pd
import streamlit as st
import models
import utils
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from ui import visualize
from logic import editor_handler
from metric_policy import resolve_metric_policy
from supabase_config import sb

@st.fragment
def _capture_fragment(selected_metric):
    # Isolated fragment so adjusting inputs doesn't rerender charts on every interaction.
    show_capture(selected_metric)


@st.fragment
def _viz_fragment(selected_metric):
    mid = selected_metric.get("id")
    show_key = f"show_add_chart_{mid}"
    if show_key not in st.session_state:
        # Default off for snappy mobile interactions; user can enable per-metric.
        st.session_state[show_key] = False

    show_chart = st.toggle(
        "Show chart",
        key=show_key,
        help="Charts can be slow on mobile. Turn this on when you want to review trends.",
    )
    if not show_chart:
        st.caption("Chart hidden for performance.")
        return

    dfe, m_unit, m_name = utils.collect_data(selected_metric)
    if dfe is not None and not dfe.empty:
        visualize.show_visualizations(
            dfe,
            m_unit,
            m_name,
            metric_kind=selected_metric.get("metric_kind"),
            unit_type=selected_metric.get("unit_type", "float"),
            range_start=selected_metric.get("range_start"),
            range_end=selected_metric.get("range_end"),
            higher_is_better=selected_metric.get("higher_is_better", True),
            show_pills=True,
            policy=resolve_metric_policy(
                selected_metric.get("name"),
                metric_id=str(selected_metric["id"]) if selected_metric.get("id") else None,
            ),
            metric_id=str(selected_metric["id"]) if selected_metric.get("id") else None,
        )
    else:
        st.info("No data recorded for this metric yet. Add your first entry above.")


def show_tracker_suite(selected_metric):
    _capture_fragment(selected_metric)
    st.divider()
    _viz_fragment(selected_metric)

def _get_initial_datetime(mid):
    date_key = f"capture_date_{mid}"
    time_key = f"capture_time_{mid}"
    if date_key not in st.session_state:
        st.session_state[date_key] = dt.date.today()
    if time_key not in st.session_state:
        st.session_state[time_key] = dt.datetime.now().time().replace(second=0, microsecond=0)

def _get_value_input(utype, unit_name, smart_default, selected_metric, recent_values):
    if utype == "integer_range":
        rs = int(selected_metric.get("range_start", 1))
        re = int(selected_metric.get("range_end", 5))
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


def _is_strength_metric(selected_metric):
    return str(selected_metric.get("metric_kind") or "").lower() == "strength_session"


def _format_success_value(strength_payload, value, unit_name):
    """Build a user-friendly success message for either a strength workout or a numeric entry."""
    if strength_payload is not None:
        summary = strength_payload.get("summary")
        if summary:
            return summary
        load_value = strength_payload.get("load_kg")
        if load_value is not None:
            return f"{load_value} {unit_name}".strip()
        return str(value or "")

    if value is None:
        return unit_name.strip() if unit_name else ""
    return f"{value} {unit_name}".strip()


def _get_previous_strength_session(mid):
    """Fetch the most recent strength session for baseline comparison."""
    try:
        res = sb.table("entries") \
            .select("*") \
            .eq("metric_id", mid) \
            .order("recorded_at", desc=True) \
            .limit(1) \
            .execute()
        if res and res.data:
            entry = res.data[0]
            sets = entry.get("sets", [])
            if sets:
                return {
                    "load_kg": entry.get("load_kg"),
                    "sets": sets,
                    "recorded_at": entry.get("recorded_at"),
                    "id": entry.get("id")
                }
    except Exception:
        pass
    return None


def _render_strength_workout_form(mid, unit_name):
    st.caption("Structured workout")

    state_key = f"strength_sets_state_{mid}"

    if state_key not in st.session_state:
        st.session_state[state_key] = []

    sets = st.session_state[state_key]
    
    # Show previous session as baseline
    previous_session = _get_previous_strength_session(mid)
    if previous_session:
        with st.expander("📊 Previous Session (Baseline)", expanded=False):
            prev_sets = previous_session.get("sets", [])
            if prev_sets:
                prev_date = previous_session.get("recorded_at", "")
                if prev_date:
                    try:
                        prev_date_str = pd.to_datetime(prev_date).strftime('%d %b %Y')
                    except:
                        prev_date_str = "Unknown"
                else:
                    prev_date_str = "Unknown"
                
                # Show individual sets on one line with separator
                if prev_sets:
                    set_strs = [f"Set {i+1}: {s.get('load_kg', 0):.1f} kg × {s.get('reps', 0)} reps" 
                               for i, s in enumerate(prev_sets) if isinstance(s, dict)]
                    if set_strs:
                        st.caption(" — ".join(set_strs))
            else:
                st.caption("No set data available")

    # Display existing sets with edit/delete options - compact layout
    if sets:
        st.subheader("Your Sets")
        for i, set_data in enumerate(sets):
            col1, col2 = st.columns([4, 1])
            with col1:
                st.info(f"Set {i+1}: {set_data['load_kg']:.1f} kg × {set_data['reps']} reps")
            with col2:
                col_edit, col_del = st.columns([1, 1])
                with col_edit:
                    if st.button("✏️", key=f"edit_{mid}_{i}", help="Edit", use_container_width=True):
                        edit_key = f"editing_set_{mid}_{i}"
                        if edit_key not in st.session_state:
                            st.session_state[edit_key] = False
                        st.session_state[edit_key] = not st.session_state[edit_key]
                        st.rerun()
                with col_del:
                    if st.button("❌", key=f"delete_{mid}_{i}", help="Delete", use_container_width=True):
                        sets.pop(i)
                        st.session_state[state_key] = sets
                        for j in range(len(sets)):
                            st.session_state.pop(f"editing_set_{mid}_{j}", None)
                        st.rerun()
            
            # Show edit form if in edit mode
            edit_key = f"editing_set_{mid}_{i}"
            if st.session_state.get(edit_key, False):
                with st.expander(f"Edit Set {i+1}", expanded=True):
                    col_a, col_b = st.columns([3, 1])
                    with col_a:
                        edit_load = st.number_input(
                            "Load (kg)",
                            value=float(set_data['load_kg']),
                            min_value=0.0,
                            step=1.0,
                            format="%.1f",
                            key=f"edit_load_{mid}_{i}",
                            label_visibility="collapsed"
                        )
                    with col_b:
                        edit_reps = st.number_input(
                            "Reps",
                            value=int(set_data['reps']),
                            min_value=1,
                            step=1,
                            key=f"edit_reps_{mid}_{i}",
                            label_visibility="collapsed"
                        )
                    if st.button("✅ Save", key=f"save_set_{mid}_{i}", type="primary", use_container_width=True):
                        sets[i] = {"load_kg": float(edit_load), "reps": int(edit_reps)}
                        st.session_state[state_key] = sets
                        st.session_state[edit_key] = False
                        st.success(f"Set {i+1} updated!")
                        st.rerun()

    # Add new set form - compact layout for mobile
    with st.expander("➕ Add Set", expanded=len(sets) == 0):
        col1, col2 = st.columns([3, 1])
        with col1:
            new_load = st.number_input(
                "Load (kg)",
                min_value=0.0,
                step=1.0,
                format="%.1f",
                key=f"new_load_{mid}",
                label_visibility="collapsed"
            )
        with col2:
            new_reps = st.number_input(
                "Reps",
                min_value=1,
                step=1,
                value=5,
                key=f"new_reps_{mid}",
                label_visibility="collapsed"
            )
        # Button below the inputs for better mobile layout
        if st.button("✅ Add Set", key=f"add_set_{mid}", type="primary", use_container_width=True):
            sets.append({"load_kg": float(new_load), "reps": int(new_reps)})
            st.session_state[state_key] = sets
            st.success(f"Set {len(sets)} added!")
            st.rerun()

    if not sets:
        st.warning("Add at least one set.")
        return None

    # Create summary
    summary_load = sets[0]["load_kg"]
    reps_series = [str(int(s["reps"])) for s in sets]
    summary = f"{summary_load:.1f} kg × {'/'.join(reps_series)} reps × {len(sets)} sets"
    return {
        "load_kg": float(summary_load),
        "sets": sets,
        "summary": summary,
    }

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
    return models.get_recent_numeric_values(str(metric_id), limit=limit)

# In capture.py

def show_capture(selected_metric):
    mid = selected_metric.get("id")
    unit_name = selected_metric.get("unit_name", "")
    kind = selected_metric.get("metric_kind")
    if kind == "score":
        utype = "integer_range"
    elif kind == "count":
        utype = "integer"
    elif kind == "quantitative":
        utype = "float"
    else:
        utype = selected_metric.get("unit_type", "float")
    
    # 1. Fetch smart defaults
    last_entry = models.get_latest_entry_only(mid)
    recent_values = _get_recent_values(mid) if utype not in ("integer", "integer_range") else []
    fallback = selected_metric.get("range_start", 0.0)
    smart_default = last_entry['value'] if last_entry else float(fallback if fallback is not None else 0.0)

    with st.container(border=True):
        if selected_metric.get("description"):
            st.caption(selected_metric["description"])

        _get_initial_datetime(mid)
        
        when_key = f"capture_when_{mid}"
        if when_key not in st.session_state:
            st.session_state[when_key] = "Now"

        # Outside the form so switching options immediately updates the UI
        when_selection = st.pills(
            "When",
            options=["Now", "Yesterday", "Custom"],
            selection_mode="single",
            key=when_key,
            label_visibility="collapsed",
        )
        
        # Handle strength workout form separately (outside the main form to avoid nested form issues)
        strength_payload = None
        if _is_strength_metric(selected_metric):
            # Strength workout form - must be outside the main form due to button usage
            with st.container(border=True):
                strength_payload = _render_strength_workout_form(mid, unit_name)
                if strength_payload is not None:
                    # Store workout data in session state for form submission
                    st.session_state[f"strength_load_{mid}"] = strength_payload["load_kg"]
                    st.session_state[f"strength_sets_{mid}"] = strength_payload["sets"]
        else:
            val = _get_value_input(utype, unit_name, smart_default, selected_metric, recent_values)
            # Store the value in session state for form submission
            st.session_state[f"numeric_value_{mid}"] = val

        # 3. Form Start
        with st.form(f"capture_entry_submit_{mid}", border=False):
            date_input = st.session_state.get(f"capture_date_{mid}", dt.date.today())
            time_input = st.session_state.get(
                f"capture_time_{mid}",
                dt.datetime.now().time().replace(second=0, microsecond=0),
            )

            if when_selection == "Custom":
                date_input = st.date_input("📅 Date", key=f"capture_date_{mid}")
                time_input = st.time_input("⏰ Time", step=60, key=f"capture_time_{mid}")

            # --- NEW LOCATION: Inside form, below value ---
            target_action = None
            if utype != "integer_range":
                st.write("") # Small spacer
                st.caption("Target for next session")
                target_action = st.pills(
                    "Target",
                    options=["Reduce", "Stay", "Increase", "Pause"],
                    selection_mode="single",
                    key=f"target_{mid}",
                    label_visibility="collapsed"
                )
                st.write("") # Small spacer
            # ----------------------------------------------

            submitted = st.form_submit_button("Add Entry", use_container_width=True, type="primary")
            
            if submitted:
                if when_selection == "Yesterday":
                    final_dt = dt.datetime.combine(
                        dt.date.today() - dt.timedelta(days=1),
                        dt.time(12, 0),
                    )
                elif when_selection == "Custom":
                    final_dt = dt.datetime.combine(date_input, time_input)
                else:
                    final_dt = dt.datetime.now().replace(second=0, microsecond=0)
                
                entry_payload = {
                    "metric_id": mid,
                    "recorded_at": final_dt.isoformat(),
                    "target_action": target_action,
                }
                if _is_strength_metric(selected_metric):
                    entry_payload["value"] = st.session_state[f"strength_load_{mid}"]
                    entry_payload["load_kg"] = st.session_state[f"strength_load_{mid}"]
                    entry_payload["sets"] = st.session_state[f"strength_sets_{mid}"]
                else:
                    entry_payload["value"] = st.session_state[f"numeric_value_{mid}"]

                # Save to DB
                models.create_entry(entry_payload)
                
                # Cleanup & Cache Clearing
                editor_handler.reset_editor_state(f"data_{mid}", mid)
                
                if hasattr(models.get_latest_entry_only, "clear"):
                    models.get_latest_entry_only.clear()
                if hasattr(models.get_entries, "clear"):
                    models.get_entries.clear()
                if hasattr(models.get_recent_numeric_values, "clear"):
                    models.get_recent_numeric_values.clear()
                
                # CRITICAL: Clear the landing page cache so the badge appears instantly
                models.get_all_entries_bulk.clear()

                # Get the value for success message
                if _is_strength_metric(selected_metric):
                    success_strength_payload = {
                        "load_kg": st.session_state[f"strength_load_{mid}"],
                        "sets": st.session_state[f"strength_sets_{mid}"],
                        "summary": f"{st.session_state[f'strength_load_{mid}']:.1f} kg workout"
                    }
                    success_value = _format_success_value(success_strength_payload, None, unit_name)
                else:
                    success_value = _format_success_value(None, st.session_state[f"numeric_value_{mid}"], unit_name)
                st.success(f"Saved: {success_value}")
                
                # Small delay to let user see success message before reload
                import time
                time.sleep(0.5)
                # Full rerun to ensure the visualization fragment updates.
                st.rerun()
