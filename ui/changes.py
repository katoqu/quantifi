import datetime as dt

import streamlit as st

import models
import utils


def _parse_iso_datetime(value):
    if not value:
        return None
    try:
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        return dt.datetime.fromisoformat(value)
    except ValueError:
        return None


def show_changes():
    st.subheader("Lifestyle Changes")

    cats = models.get_categories() or []
    if not cats:
        st.info("Create a category first (Settings → Categories).")
        return

    if "edit_change_event_id" not in st.session_state:
        st.session_state["edit_change_event_id"] = None

    cat_labels = {c["id"]: c.get("name", "").title() for c in cats}
    sorted_cat_ids = sorted(cat_labels.keys(), key=lambda cid: cat_labels[cid].lower())

    with st.container(border=True):
        st.caption("Log a change")

        when_key = "change_when"
        if when_key not in st.session_state:
            st.session_state[when_key] = "Today"

        when_selection = st.pills(
            "When",
            options=["Now", "Today", "Yesterday", "Custom"],
            selection_mode="single",
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
            notes = st.text_area("Notes", placeholder="Optional context, routine details, exceptions…")

            date_input = dt.date.today()
            time_input = dt.datetime.now().time().replace(second=0, microsecond=0)
            if when_selection == "Custom":
                date_input = st.date_input("📅 Date", value=date_input)
                time_input = st.time_input("⏰ Time", value=time_input, step=60)

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
                    }
                )
                if hasattr(models.get_change_events, "clear"):
                    models.get_change_events.clear()
                utils.finalize_action("Change saved", icon="📝")
                st.rerun()

    events = models.get_change_events() or []
    if not events:
        st.info("No changes logged yet.")
        return

    with st.container(border=True):
        st.caption("Recent changes")
        for ev in events:
            ev_id = ev.get("id")
            cat_name = (ev.get("categories") or {}).get("name")
            cat_label = (cat_name.title() if cat_name else "Uncategorized")
            ts = _parse_iso_datetime(ev.get("recorded_at"))
            ts_label = ts.strftime("%Y-%m-%d %H:%M") if ts else str(ev.get("recorded_at"))

            with st.container(border=True):
                col_main, col_edit, col_delete = st.columns([8, 2, 2])
                with col_main:
                    st.markdown(f"**{cat_label}:** {ev.get('title', '')}")
                    st.caption(ts_label)

                with col_edit:
                    if ev_id and st.button("Edit", key=f"edit_change_{ev_id}", use_container_width=True):
                        st.session_state["edit_change_event_id"] = ev_id
                        st.rerun()

                with col_delete:
                    if ev_id and st.button("Delete", key=f"delete_change_{ev_id}", type="secondary", use_container_width=True):
                        models.delete_change_event(ev_id)
                        if hasattr(models.get_change_events, "clear"):
                            models.get_change_events.clear()
                        if st.session_state.get("edit_change_event_id") == ev_id:
                            st.session_state["edit_change_event_id"] = None
                        utils.finalize_action("Deleted", icon="🗑️")
                        st.rerun()

                if st.session_state.get("edit_change_event_id") == ev_id:
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
                            "Notes",
                            value=ev.get("notes") or "",
                            key=f"edit_change_notes_{ev_id}",
                        )

                        base_dt = ts or dt.datetime.now().replace(second=0, microsecond=0)
                        edit_date = st.date_input(
                            "📅 Date",
                            value=base_dt.date(),
                            key=f"edit_change_date_{ev_id}",
                        )
                        edit_time = st.time_input(
                            "⏰ Time",
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
                        st.session_state["edit_change_event_id"] = None
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
                            st.session_state["edit_change_event_id"] = None
                            utils.finalize_action("Updated", icon="✏️")
                            st.rerun()
                else:
                    if ev.get("notes"):
                        st.write(ev["notes"])
                    else:
                        st.caption("No notes.")
