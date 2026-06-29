import pandas as pd
import streamlit as st
import models
import utils
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from ui import visualize
from logic import editor_handler
from metric_policy import resolve_metric_policy

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


def _render_strength_workout_form(mid, unit_name):
    st.caption("Structured workout")

    default_sets = [{"load_kg": 0.0, "reps": 5}]
    state_key = f"strength_sets_state_{mid}"
    widget_key = f"strength_sets_editor_{mid}"

    if state_key not in st.session_state:
        st.session_state[state_key] = pd.DataFrame(default_sets)

    editor_df = st.session_state[state_key]
    if not isinstance(editor_df, pd.DataFrame):
        editor_df = pd.DataFrame(default_sets)
    if editor_df.empty:
        editor_df = pd.DataFrame(default_sets)
        st.session_state[state_key] = editor_df

    edited_df = st.data_editor(
        editor_df,
        key=widget_key,
        hide_index=True,
        use_container_width=True,
        num_rows="dynamic",
        column_order=["load_kg", "reps"],
        column_config={
            "load_kg": st.column_config.NumberColumn("Load (kg)", step=1.0, format="%.1f"),
            "reps": st.column_config.NumberColumn("Reps", step=1, format="%d"),
        },
    )

    if edited_df is not None:
        if isinstance(edited_df, pd.DataFrame):
            st.session_state[state_key] = edited_df.reset_index(drop=True)
            editor_df = edited_df.reset_index(drop=True)
        else:
            st.session_state[state_key] = pd.DataFrame(default_sets)
            editor_df = pd.DataFrame(default_sets)

    if editor_df.empty:
        st.warning("Add at least one set.")
        return None

    normalized_sets = []
    for _, row in editor_df.iterrows():
        load_value = row.get("load_kg")
        reps_value = row.get("reps")
        if pd.isna(load_value) or pd.isna(reps_value):
            continue
        normalized_sets.append({
            "load_kg": float(load_value),
            "reps": int(reps_value),
        })

    if not normalized_sets:
        st.warning("Add at least one valid set.")
        return None

    summary_load = normalized_sets[0].get("load_kg", 0.0)
    reps_series = [str(int(s.get("reps", 0))) for s in normalized_sets]
    return {
        "load_kg": float(summary_load),
        "sets": normalized_sets,
        "summary": f"{summary_load:.1f} kg × {'/'.join(reps_series)} reps × {len(normalized_sets)} sets",
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

            strength_payload = None
            if _is_strength_metric(selected_metric):
                strength_payload = _render_strength_workout_form(mid, unit_name)
            else:
                val = _get_value_input(utype, unit_name, smart_default, selected_metric, recent_values)

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
                if strength_payload is not None:
                    entry_payload["value"] = strength_payload["load_kg"]
                    entry_payload["load_kg"] = strength_payload["load_kg"]
                    entry_payload["sets"] = strength_payload["sets"]
                else:
                    entry_payload["value"] = val

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

                success_value = _format_success_value(strength_payload, val if "val" in locals() else None, unit_name)
                st.success(f"Saved: {success_value}")
                
                # Small delay to let user see success message before reload
                import time
                time.sleep(0.5)
                # Full rerun to ensure the visualization fragment updates.
                st.rerun()
