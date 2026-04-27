"""Dialog components for metric management."""

from typing import Any
import streamlit as st
import models
import utils


_METRIC_KIND_OPTIONS = ["quantitative", "count", "score"]
_KIND_TO_UNIT_TYPE = {"quantitative": "float", "count": "integer", "score": "integer_range"}


def _infer_metric_kind(metric):
    kind = metric.get("metric_kind")
    if kind in _METRIC_KIND_OPTIONS:
        return kind
    utype = (metric.get("unit_type") or "float").strip().lower()
    if utype == "integer_range":
        return "score"
    if utype == "integer":
        return "count"
    return "quantitative"


def _can_convert_kind(from_kind, to_kind):
    if from_kind == to_kind:
        return False
    if from_kind == "score" and to_kind == "count":
        return True
    if from_kind == "count" and to_kind == "score":
        return True
    return False


def _metric_search_label(metric, cat_labels):
    cat_id = metric.get("category_id")
    cat = "Uncat" if cat_id is None else cat_labels.get(cat_id, "Uncat")
    return f"{cat} • {utils.format_metric_label(metric)}"


def _metric_matches_query(metric, cat_labels, query: str) -> bool:
    q = (query or "").strip().lower()
    if not q:
        return True
    tokens = [t for t in q.replace("(", " ").replace(")", " ").split() if t]
    if not tokens:
        return True

    cat_id = metric.get("category_id")
    cat = "uncat" if cat_id is None else (cat_labels.get(cat_id, "uncat") or "uncat")
    haystack = " ".join(
        [
            str(metric.get("name") or ""),
            str(metric.get("unit_name") or ""),
            str(cat or ""),
        ]
    ).lower()
    return all(t in haystack for t in tokens)


def _delete_phrase_matches(metric_name: str, typed_text: str) -> bool:
    expected = f"delete {utils.normalize_name(metric_name or '')}"
    return utils.normalize_name(typed_text or "") == expected


@st.dialog("Convert Metric Kind")
def show_convert_metric_kind_dialog(metric):
    """Dialog to convert metric kind while validating data constraints."""
    mid = metric.get("id")
    if not mid:
        st.error("Missing metric id.")
        return

    current_kind = _infer_metric_kind(metric)
    entry_count = models.get_entry_count(mid)
    st.caption(f"Metric has {entry_count} entries. Conversion changes aggregation + visualization defaults.")

    allowed_targets = [k for k in _METRIC_KIND_OPTIONS if _can_convert_kind(current_kind, k)]
    if not allowed_targets:
        st.info("No supported conversions for this metric yet.")
        return

    target_kind = st.selectbox("Convert to", options=allowed_targets, index=0)

    rs = metric.get("range_start", 1)
    re = metric.get("range_end", 5)
    hib = bool(metric.get("higher_is_better", True))

    if target_kind == "score":
        st.caption("Score requires bounds and a direction (higher-is-better). Existing values must fit inside the bounds.")
        c1, c2 = st.columns(2)
        rs = c1.number_input("Min", value=int(rs or 1), step=1, key=f"conv_rs_{mid}")
        re = c2.number_input("Max", value=int(re or 5), step=1, key=f"conv_re_{mid}")
        hib = st.toggle("Higher is better", value=hib, key=f"conv_hib_{mid}")
        if rs >= re:
            st.error("Max must be strictly greater than Min.")
            return

        actual_min, actual_max = models.get_metric_value_bounds(mid)
        if actual_min is not None and actual_max is not None:
            if rs > actual_min:
                st.error(f"Existing data has values as low as {actual_min}; Min must be ≤ {actual_min}.")
                return
            if re < actual_max:
                st.error(f"Existing data has values as high as {actual_max}; Max must be ≥ {actual_max}.")
                return

        if models.metric_has_fractional_values(mid):
            st.error("Existing values include decimals; score metrics require whole numbers. Fix data first or keep as count/quantitative.")
            return

    if target_kind == "count":
        st.caption("Count metrics are treated as totals per period (weekly/monthly views use sums). Range limits will be removed.")
        if not bool(metric.get("higher_is_better", True)):
            st.info("Note: 'higher is better' is ignored for counts (no red/green scale).")

    confirm = st.checkbox("I understand this changes historical aggregation/visuals.", value=False, key=f"conv_confirm_{mid}")
    if not confirm:
        return

    payload: dict[str, Any] = {
        "metric_kind": target_kind,
        "unit_type": _KIND_TO_UNIT_TYPE[target_kind],
    }
    if target_kind == "score":
        payload["range_start"] = int(rs)
        payload["range_end"] = int(re)
        payload["higher_is_better"] = bool(hib)
    elif target_kind == "count":
        payload["range_start"] = None
        payload["range_end"] = None

    if st.button("Convert", type="primary", use_container_width=True):
        models.update_metric(mid, payload)
        utils.finalize_action(f"Converted kind: {metric.get('name','Metric').title()} → {target_kind}")
        st.rerun()


@st.dialog("Browse metrics")
def show_browse_metric_dialog(metrics, cat_labels, current_id):
    """Dialog to search and select a metric from a filterable list."""
    if "exclude_archived_metrics" not in st.session_state:
        st.session_state["exclude_archived_metrics"] = True

    hide_archived = st.checkbox("Hide archived", key="exclude_archived_metrics")
    query = st.text_input(
        "Search",
        placeholder="Type a name, unit, or category…",
        key="metric_browse_query",
    )

    visible_metrics = (
        [m for m in metrics if not m.get("is_archived") or str(m.get("id")) == str(current_id)]
        if hide_archived
        else metrics
    )

    category_ids = {m.get("category_id") for m in visible_metrics}
    category_options = ["ALL"]
    category_options += sorted(
        [cid for cid in category_ids if cid is not None],
        key=lambda cid: cat_labels.get(cid, "").lower(),
    )
    if None in category_ids:
        category_options.append("UNCAT")

    def _category_label(cid):
        if cid == "ALL":
            return "All"
        if cid == "UNCAT":
            return "Uncat"
        return cat_labels.get(cid, "Uncat")

    def _unique_labels(keys):
        labels = []
        seen = set()
        for k in keys:
            base = _category_label(k)
            label = base
            if label in seen:
                suffix = str(k)[-4:]
                label = f"{base} · {suffix}"
            seen.add(label)
            labels.append(label)
        return labels

    category_labels = _unique_labels(category_options)
    label_to_category = {label: cid for (label, cid) in zip(category_labels, category_options)}

    selected_category = "ALL"
    if len(category_options) <= 12:
        cat_key = "metric_browse_category"
        if cat_key not in st.session_state:
            st.session_state[cat_key] = category_labels[0]
        picked_label = st.pills(
            "Category",
            options=category_labels,
            selection_mode="single",
            key=cat_key,
        )
        selected_category = label_to_category.get(picked_label, "ALL")
    else:
        selected_category = st.selectbox(
            "Category",
            options=category_options,
            format_func=_category_label,
            index=0,
        )

    if selected_category == "ALL":
        filtered_metrics = visible_metrics
    elif selected_category == "UNCAT":
        filtered_metrics = [m for m in visible_metrics if m.get("category_id") is None]
    else:
        filtered_metrics = [m for m in visible_metrics if m.get("category_id") == selected_category]

    filtered_metrics = [m for m in filtered_metrics if _metric_matches_query(m, cat_labels, query)]
    filtered_metrics = sorted(filtered_metrics, key=lambda m: (m.get("name", "") or "").lower())

    if not filtered_metrics:
        st.caption("No matching metrics.")
        return

    show_all = st.toggle("Show all results", key="metric_browse_show_all")

    max_items = 200 if show_all else 30
    shown_metrics = filtered_metrics[:max_items]

    st.caption(f"{len(filtered_metrics)} result(s). Tap a metric to select it.")
    for m in shown_metrics:
        mid = m["id"]
        label = _metric_search_label(m, cat_labels)
        is_selected = str(mid) == str(current_id)
        if st.button(label, key=f"metric_pick_{mid}", use_container_width=True, type="primary" if is_selected else "secondary"):
            st.session_state["last_active_mid"] = mid
            st.rerun()

    if not show_all and len(filtered_metrics) > max_items:
        st.info('Refine your search or enable "Show all results".')

    st.button("Cancel", use_container_width=True)


@st.dialog("Delete Metric")
def show_confirm_metric_delete_dialog(metric):
    """Dialog to permanently delete a metric and its entries."""
    mid = metric.get("id")
    if not mid:
        st.error("Missing metric id.")
        return

    metric_name = str(metric.get("name") or "metric")
    entry_count = models.get_entry_count(mid)
    entry_word = "entry" if entry_count == 1 else "entries"

    st.error("This permanently deletes this metric.")
    st.caption(
        f"It will also delete {entry_count} {entry_word} linked to this metric. This cannot be undone."
    )

    phrase = f"delete {utils.normalize_name(metric_name)}"
    typed = st.text_input(
        f"Type `{phrase}` to confirm",
        key=f"metric_delete_phrase_{mid}",
    )
    acknowledged = st.checkbox(
        "I understand this action is permanent.",
        key=f"metric_delete_ack_{mid}",
        value=False,
    )
    can_delete = acknowledged and _delete_phrase_matches(metric_name, typed)

    if st.button(
        "Delete metric",
        type="primary",
        use_container_width=True,
        disabled=not can_delete,
    ):
        models.delete_metric(mid)
        if str(st.session_state.get("last_active_mid")) == str(mid):
            st.session_state.pop("last_active_mid", None)
        utils.finalize_action(f"Deleted: {metric_name.title()}", icon="🗑️")
        st.rerun()


@st.dialog("Confirm Metric Update")
def show_confirm_metric_update_dialog(m, new_payload, cat_options=None, new_cat_name=None):
    """Dialog to review and confirm metric changes before saving."""
    st.markdown("### Review Changes")
    
    # Identify what actually changed
    changes = []
    
    # 1. Name check
    if m['name'].lower() != new_payload['name'].lower():
        changes.append({
            "label": "Name",
            "old": m['name'].title(),
            "new": new_payload['name'].title()
        })
        
    # 2. Description check (handle None vs empty string)
    old_desc = (m.get('description') or "").strip()
    new_desc = (new_payload.get('description') or "").strip()
    if old_desc != new_desc:
        changes.append({
            "label": "Description",
            "old": old_desc if old_desc else "(Empty)",
            "new": new_desc if new_desc else "(Empty)"
        })
        
    # 3. Unit check
    old_unit = (m.get('unit_name') or "").lower()
    new_unit = (new_payload.get('unit_name') or "").lower()
    if old_unit != new_unit:
        changes.append({
            "label": "Unit",
            "old": m.get('unit_name', 'None').title(),
            "new": new_payload.get('unit_name', 'None').title()
        })

    # 4. Category check
    if m.get('category_id') != new_payload.get('category_id'):
        cat_options = cat_options or {}
        old_cat_id = m.get("category_id")
        new_cat_id = new_payload.get("category_id")
        old_label = cat_options.get(old_cat_id, "Uncat")
        if new_cat_id in cat_options:
            new_label = cat_options.get(new_cat_id, "Uncat")
        elif new_cat_id is None:
            new_label = "Uncat"
        else:
            new_label = (new_cat_name or "Uncat").title()
        changes.append({
            "label": "Category",
            "old": old_label,
            "new": new_label
        })

    # 5. Range check (only if applicable)
    if (m.get("unit_type") == "integer_range") or (new_payload.get("unit_type") == "integer_range"):
        if m.get("range_start") != new_payload.get("range_start") or \
           m.get("range_end") != new_payload.get("range_end"):
            changes.append({
                "label": "Range",
                "old": f"{m.get('range_start')} - {m.get('range_end')}",
                "new": f"{new_payload.get('range_start')} - {new_payload.get('range_end')}"
            })

    # 6. Kind check
    old_kind = _infer_metric_kind(m)
    new_kind = new_payload.get("metric_kind", old_kind)
    if new_kind != old_kind:
        changes.append(
            {
                "label": "Kind",
                "old": old_kind,
                "new": new_kind,
            }
        )

    # 7. Score direction check
    if new_kind == "score":
        old_dir = bool(m.get("higher_is_better", True))
        new_dir = bool(new_payload.get("higher_is_better", True))
        if old_dir != new_dir:
            changes.append(
                {
                    "label": "Higher Is Better",
                    "old": "Yes" if old_dir else "No",
                    "new": "Yes" if new_dir else "No",
                }
            )

    # Render the UI based on changes
    if not changes:
        st.info("No changes detected.")
    else:
        for change in changes:
            with st.container():
                st.write(f"**{change['label']}**")
                col_a, col_b = st.columns(2)
                col_a.caption("Current")
                col_a.write(change['old'])
                col_b.caption("Proposed")
                col_b.write(f":green[{change['new']}]")
                st.divider()

    st.warning("Updating these settings will change how historical data is labeled.")

    col_save, col_cancel = st.columns(2)
    if col_save.button("Confirm & Save", type="primary", use_container_width=True, disabled=not changes):
        with st.spinner("Updating..."):
            models.update_metric(m['id'], new_payload)
        utils.finalize_action(f"Updated: {new_payload['name'].title()}")
        st.rerun()
    if col_cancel.button("Cancel", use_container_width=True):
        st.session_state[f"ed_nm_{m['id']}"] = m.get("name", "")
        st.session_state[f"ed_desc_{m['id']}"] = m.get("description", "") or ""
        st.session_state[f"ed_un_{m['id']}"] = m.get("unit_name", "") or ""
        st.session_state[f"ed_ct_{m['id']}"] = m.get("category_id")
        st.session_state.pop(f"inline_cat_{m['id']}", None)
        st.session_state[f"rs_{m['id']}"] = _int_or_default(m.get("range_start"), 1)
        st.session_state[f"re_{m['id']}"] = _int_or_default(m.get("range_end"), 5)
        st.rerun()


def _int_or_default(value, default):
    """Helper to convert value to int or return default."""
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default
