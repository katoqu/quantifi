import datetime as dt

import streamlit as st

import models
import utils


_EDIT_KEY = "edit_change_event_id"
_END_KEY = "end_change_event_id"
_REVIVE_KEY = "revive_change_event_id"
_FILTER_PILL_KEY = "change_filter_pill"
_SHOW_ARCHIVED_KEY = "show_archived_changes"
_RECENT_LIMIT = 8


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def _render_markdown_notes(notes: str | None):
    if not notes:
        st.caption("No notes.")
        return
    st.markdown(notes)


def _format_dt_short(value) -> str:
    ts = _parse_iso_datetime(value)
    return ts.strftime("%Y-%m-%d %H:%M") if ts else "Unknown"


def _sort_event_desc(event):
    ts = _parse_iso_datetime(event.get("recorded_at"))
    return ts.timestamp() if ts else float("-inf")


def _sort_recent_desc(event):
    ts = _parse_iso_datetime(event.get("end_at")) or _parse_iso_datetime(event.get("recorded_at"))
    return ts.timestamp() if ts else float("-inf")


def _truncate(text: str, limit: int = 72) -> str:
    text = str(text or "").strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "..."


def _clear_transient_event_actions():
    st.session_state[_END_KEY] = None
    st.session_state[_REVIVE_KEY] = None


def _clear_all_event_modes():
    st.session_state[_EDIT_KEY] = None
    _clear_transient_event_actions()


def _event_label(ev):
    title = _truncate(ev.get("title") or "Untitled change")
    if ev.get("is_archived"):
        return f"[Archived] {title}"
    return title


def _persist_change_update(event_id, payload, success_msg, icon):
    models.update_change_event(event_id, payload)
    if hasattr(models.get_change_events, "clear"):
        models.get_change_events.clear()
    _clear_all_event_modes()
    utils.finalize_action(success_msg, icon=icon)
    st.rerun()


def _pills_value(label: str, *, options: list, key: str, label_visibility: str = "visible", format_func=None):
    selected = st.pills(
        label,
        options=options,
        key=key,
        selection_mode="single",
        label_visibility=label_visibility,
        format_func=format_func,
    )
    if selected in options:
        return selected
    existing = st.session_state.get(key)
    if existing in options:
        return existing
    return options[0] if options else None


def _render_event_meta(ev):
    cat_name = (ev.get("categories") or {}).get("name")
    cat_label = cat_name.title() if cat_name else "Uncategorized"

    started = _format_dt_short(ev.get("recorded_at"))
    ended = _format_dt_short(ev.get("end_at")) if ev.get("is_archived") else None

    if ended:
        st.caption(f"Category: {cat_label} | Started: {started} | Ended: {ended}")
    else:
        st.caption(f"Category: {cat_label} | Started: {started}")


def _category_label_for_event(ev, cat_labels):
    cat_name = (ev.get("categories") or {}).get("name")
    if cat_name:
        return cat_name.title()
    cat_id = ev.get("category_id")
    if cat_id is None:
        return "Uncategorized"
    return cat_labels.get(cat_id, "Uncategorized")


def _render_end_form(ev):
    ev_id = ev.get("id")
    if st.session_state.get(_END_KEY) != ev_id:
        return

    with st.form(f"end_change_form_{ev_id}", border=False):
        st.caption("Pick the date/time when this routine ended.")
        now = dt.datetime.now().replace(second=0, microsecond=0)
        end_date = st.date_input("End date", value=now.date(), key=f"end_change_date_{ev_id}")
        end_time = st.time_input("End time", value=now.time(), step=60, key=f"end_change_time_{ev_id}")

        c1, c2 = st.columns(2)
        confirm_clicked = c1.form_submit_button("Confirm End Date", type="primary", use_container_width=True)
        cancel_clicked = c2.form_submit_button("Cancel", use_container_width=True)

    if cancel_clicked:
        st.session_state[_END_KEY] = None
        st.rerun()

    if confirm_clicked:
        end_at = dt.datetime.combine(end_date, end_time)
        _persist_change_update(
            ev_id,
            {
                "end_at": end_at.isoformat(),
                "is_archived": True,
            },
            success_msg="Routine archived",
            icon="📦",
        )


def _render_revive_form(ev):
    ev_id = ev.get("id")
    if st.session_state.get(_REVIVE_KEY) != ev_id:
        return

    with st.form(f"revive_change_form_{ev_id}", border=False):
        st.caption("Pick a new start date/time to revive this routine.")
        now = dt.datetime.now().replace(second=0, microsecond=0)
        start_date = st.date_input("New start date", value=now.date(), key=f"revive_change_date_{ev_id}")
        start_time = st.time_input("New start time", value=now.time(), step=60, key=f"revive_change_time_{ev_id}")

        c1, c2 = st.columns(2)
        confirm_clicked = c1.form_submit_button("Confirm New Start Date", type="primary", use_container_width=True)
        cancel_clicked = c2.form_submit_button("Cancel", use_container_width=True)

    if cancel_clicked:
        st.session_state[_REVIVE_KEY] = None
        st.rerun()

    if confirm_clicked:
        recorded_at = dt.datetime.combine(start_date, start_time)
        _persist_change_update(
            ev_id,
            {
                "recorded_at": recorded_at.isoformat(),
                "end_at": None,
                "is_archived": False,
            },
            success_msg="Routine revived",
            icon="♻️",
        )


def _render_edit_form(ev, sorted_cat_ids, cat_labels):
    ev_id = ev.get("id")
    if st.session_state.get(_EDIT_KEY) != ev_id:
        return

    ts = _parse_iso_datetime(ev.get("recorded_at"))
    base_dt = ts or dt.datetime.now().replace(second=0, microsecond=0)

    with st.form(f"edit_change_form_{ev_id}", border=False):
        current_category_id = ev.get("category_id")
        if current_category_id not in sorted_cat_ids:
            current_category_id = sorted_cat_ids[0]

        edit_category_id = st.selectbox(
            "Category",
            options=sorted_cat_ids,
            format_func=lambda x: cat_labels.get(x, "Unknown"),
            index=sorted_cat_ids.index(current_category_id),
            key=f"edit_change_category_{ev_id}",
        )
        edit_title = st.text_input(
            "Title",
            value=ev.get("title", ""),
            key=f"edit_change_title_{ev_id}",
        )
        edit_notes = st.text_area(
            "Notes (Markdown supported)",
            value=ev.get("notes") or "",
            key=f"edit_change_notes_{ev_id}",
            height=260,
        )

        edit_date = st.date_input(
            "Start date",
            value=base_dt.date(),
            key=f"edit_change_date_{ev_id}",
        )
        edit_time = st.time_input(
            "Start time",
            value=base_dt.time().replace(second=0, microsecond=0),
            step=60,
            key=f"edit_change_time_{ev_id}",
        )

        col_save, col_cancel = st.columns(2)
        save_clicked = col_save.form_submit_button(
            "Save Changes",
            use_container_width=True,
            type="primary",
        )
        cancel_clicked = col_cancel.form_submit_button(
            "Cancel",
            use_container_width=True,
        )

    if cancel_clicked:
        st.session_state[_EDIT_KEY] = None
        st.rerun()

    if save_clicked:
        norm_title = (edit_title or "").strip()
        if not norm_title:
            st.warning("Title cannot be empty.")
        else:
            recorded_at = dt.datetime.combine(edit_date, edit_time)
            models.update_change_event(
                ev_id,
                {
                    "title": norm_title,
                    "notes": (edit_notes.strip() if edit_notes and edit_notes.strip() else None),
                    "category_id": edit_category_id,
                    "recorded_at": recorded_at.isoformat(),
                },
            )
            if hasattr(models.get_change_events, "clear"):
                models.get_change_events.clear()
            st.session_state[_EDIT_KEY] = None
            utils.finalize_action("Updated", icon="✏️")
            st.rerun()


def _render_event_common_actions(ev, *, archived):
    ev_id = ev.get("id")

    if archived:
        c1, c2, c3 = st.columns(3)
        with c1:
            if ev_id and st.button("Revive", key=f"revive_change_{ev_id}", type="primary", use_container_width=True):
                st.session_state[_REVIVE_KEY] = ev_id
                st.session_state[_EDIT_KEY] = None
                st.session_state[_END_KEY] = None
                st.rerun()
        with c2:
            if ev_id and st.button("Edit", key=f"edit_change_{ev_id}", use_container_width=True):
                st.session_state[_EDIT_KEY] = ev_id
                _clear_transient_event_actions()
                st.rerun()
        with c3:
            if ev_id and st.button("Delete", key=f"delete_change_{ev_id}", type="secondary", use_container_width=True):
                models.delete_change_event(ev_id)
                if hasattr(models.get_change_events, "clear"):
                    models.get_change_events.clear()
                _clear_all_event_modes()
                utils.finalize_action("Deleted", icon="🗑️")
                st.rerun()
    else:
        c1, c2, c3 = st.columns(3)
        with c1:
            if ev_id and st.button("Edit", key=f"edit_change_{ev_id}", use_container_width=True):
                st.session_state[_EDIT_KEY] = ev_id
                _clear_transient_event_actions()
                st.rerun()
        with c2:
            if ev_id and st.button("End routine", key=f"end_change_{ev_id}", type="primary", use_container_width=True):
                st.session_state[_END_KEY] = ev_id
                st.session_state[_EDIT_KEY] = None
                st.session_state[_REVIVE_KEY] = None
                st.rerun()
        with c3:
            if ev_id and st.button("Delete", key=f"delete_change_{ev_id}", type="secondary", use_container_width=True):
                models.delete_change_event(ev_id)
                if hasattr(models.get_change_events, "clear"):
                    models.get_change_events.clear()
                _clear_all_event_modes()
                utils.finalize_action("Deleted", icon="🗑️")
                st.rerun()


def _render_events_section(events, *, archived_override, sorted_cat_ids, cat_labels):
    for ev in events:
        ev_id = ev.get("id")
        mode_is_active = (
            st.session_state.get(_EDIT_KEY) == ev_id
            or st.session_state.get(_END_KEY) == ev_id
            or st.session_state.get(_REVIVE_KEY) == ev_id
        )

        with st.expander(_event_label(ev), expanded=mode_is_active):
            if st.session_state.get(_END_KEY) == ev_id:
                _render_end_form(ev)
                continue
            if st.session_state.get(_REVIVE_KEY) == ev_id:
                _render_revive_form(ev)
                continue
            if st.session_state.get(_EDIT_KEY) == ev_id:
                _render_edit_form(ev, sorted_cat_ids, cat_labels)
                continue

            _render_event_meta(ev)
            _render_markdown_notes(ev.get("notes"))
            st.divider()
            event_archived = bool(ev.get("is_archived")) if archived_override is None else bool(archived_override)
            _render_event_common_actions(ev, archived=event_archived)


def _apply_simple_filter(events, selected_filter, *, cat_labels):
    if selected_filter == "Recent":
        recent = sorted(events, key=_sort_recent_desc, reverse=True)[:_RECENT_LIMIT]
        return recent, f"Recent routines (last {_RECENT_LIMIT})"

    filtered = [ev for ev in events if _category_label_for_event(ev, cat_labels) == selected_filter]
    filtered = sorted(filtered, key=_sort_recent_desc, reverse=True)
    return filtered, f"Category: {selected_filter}" if filtered else "No routines match this filter yet."


def _render_create_change_panel(sorted_cat_ids, cat_labels):
    when_key = "change_when"
    if when_key not in st.session_state:
        st.session_state[when_key] = "Today"

    when_selection = _pills_value(
        "When",
        options=["Now", "Today", "Yesterday", "Custom"],
        key=when_key,
        label_visibility="collapsed",
    )

    with st.form("create_change_event", clear_on_submit=True, border=False):
        category_id = st.selectbox(
            "Category",
            options=sorted_cat_ids,
            format_func=lambda x: cat_labels.get(x, "Unknown"),
        )
        title = st.text_input("Title", placeholder="e.g., Started vegetarian nutrition")
        notes = st.text_area(
            "Notes (Markdown supported)",
            placeholder="Optional context, routine details, exceptions...",
            height=220,
        )

        date_input = dt.date.today()
        time_input = dt.datetime.now().time().replace(second=0, microsecond=0)
        if when_selection == "Custom":
            date_input = st.date_input("Date", value=date_input)
            time_input = st.time_input("Time", value=time_input, step=60)

        submitted = st.form_submit_button("Add Change", use_container_width=True, type="primary")

    if submitted:
        norm_title = title.strip()
        if not norm_title:
            st.warning("Please enter a title.")
        else:
            if when_selection == "Yesterday":
                recorded_at = dt.datetime.combine(
                    dt.date.today() - dt.timedelta(days=1),
                    dt.time(12, 0),
                )
            elif when_selection == "Today":
                recorded_at = dt.datetime.combine(dt.date.today(), dt.time(12, 0))
            elif when_selection == "Custom":
                recorded_at = dt.datetime.combine(date_input, time_input)
            else:
                recorded_at = dt.datetime.now().replace(second=0, microsecond=0)

            models.create_change_event(
                {
                    "title": norm_title,
                    "notes": (notes.strip() if notes and notes.strip() else None),
                    "category_id": category_id,
                    "recorded_at": recorded_at.isoformat(),
                    "end_at": None,
                    "is_archived": False,
                }
            )
            if hasattr(models.get_change_events, "clear"):
                models.get_change_events.clear()
            utils.finalize_action("Change saved", icon="📝")
            st.rerun()


def show_changes():
    cats = models.get_categories() or []
    if not cats:
        st.info("Create a category first (Settings -> Categories).")
        return

    if _EDIT_KEY not in st.session_state:
        st.session_state[_EDIT_KEY] = None
    if _END_KEY not in st.session_state:
        st.session_state[_END_KEY] = None
    if _REVIVE_KEY not in st.session_state:
        st.session_state[_REVIVE_KEY] = None

    cat_labels = {c["id"]: c.get("name", "").title() for c in cats}
    sorted_cat_ids = sorted(cat_labels.keys(), key=lambda cid: cat_labels[cid].lower())

    events = models.get_change_events() or []
    c_filters, c_toggle = st.columns([4, 1])
    with c_toggle:
        show_archived = st.toggle("Archived", key=_SHOW_ARCHIVED_KEY, value=False)

    visible_events = (
        sorted(events, key=_sort_recent_desc, reverse=True)
        if show_archived
        else sorted([ev for ev in events if not ev.get("is_archived", False)], key=_sort_event_desc, reverse=True)
    )
    present_categories = sorted(
        {_category_label_for_event(ev, cat_labels) for ev in visible_events},
        key=lambda x: x.lower(),
    )
    filter_options = ["Recent"] + present_categories
    with c_filters:
        selected_filter = _pills_value(
            "Filter",
            options=filter_options,
            key=_FILTER_PILL_KEY,
            label_visibility="collapsed",
        )

    utils.render_back_button(
        target_page_title="Tracker",
        target_tab="Home",
        key="back_from_changes",
    )

    with st.expander("New change", expanded=False):
        _render_create_change_panel(sorted_cat_ids, cat_labels)

    if not events:
        st.info("No changes logged yet.")
        return

    filtered_events, section_caption = _apply_simple_filter(visible_events, selected_filter, cat_labels=cat_labels)

    if not filtered_events:
        st.info("No routines match this filter yet.")
        return

    with st.container(border=True):
        st.caption(section_caption)
        _render_events_section(
            filtered_events,
            archived_override=None,
            sorted_cat_ids=sorted_cat_ids,
            cat_labels=cat_labels,
        )
