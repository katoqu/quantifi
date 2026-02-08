import streamlit as st
import models
import utils


_METRIC_KIND_OPTIONS = ["quantitative", "count", "score"]
_KIND_TO_UNIT_TYPE = {"quantitative": "float", "count": "integer", "score": "integer_range"}

def _int_or_default(value, default):
    if value is None:
        return default
    try:
        return int(value)
    except (TypeError, ValueError):
        return default


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

@st.dialog("Convert Metric Kind")
def _convert_metric_kind_dialog(metric):
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
        if actual_min is not None:
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

    payload = {
        "metric_kind": target_kind,
        "unit_type": _KIND_TO_UNIT_TYPE[target_kind],
    }
    if target_kind == "score":
        payload.update(
            {
                "range_start": int(rs),
                "range_end": int(re),
                "higher_is_better": bool(hib),
            }
        )
    elif target_kind == "count":
        payload.update({"range_start": None, "range_end": None})

    if st.button("Convert", type="primary", use_container_width=True):
        models.update_metric(mid, payload)
        utils.finalize_action(f"Converted kind: {metric.get('name','Metric').title()} → {target_kind}")
        st.rerun()

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


@st.dialog("Browse metrics")
def _browse_metric_dialog(metrics, cat_labels, current_id):
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

    id_to_metric = {m["id"]: m for m in visible_metrics}

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
        button_kwargs = {"type": "primary"} if str(mid) == str(current_id) else {}
        if st.button(label, key=f"metric_pick_{mid}", use_container_width=True, **button_kwargs):
            st.session_state["last_active_mid"] = mid
            st.rerun()

    if not show_all and len(filtered_metrics) > max_items:
        st.info("Refine your search or enable “Show all results”.")

    st.button("Cancel", use_container_width=True)

@st.dialog("Confirm Metric Update")
def _confirm_metric_update_dialog(m, new_payload, cat_options=None, new_cat_name=None):
    """Summarizes only the changed values for the user to review."""
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

def show_edit_metrics(metrics_list, cats):
    """Focused Mobile Editor: Only shows the 'Active' metric for editing."""
    st.subheader("Edit Metric")
    
    # 1. Reuse the selector to pick which metric to edit (Sticky Logic)
    active_id = st.session_state.get("last_active_mid")
    selected_metric = select_metric(metrics_list, target_id=active_id)
    
    if not selected_metric:
        st.info("Select a metric above to edit its settings.")
        return

    # Update sticky state if user changes selection here
    st.session_state["last_active_mid"] = selected_metric['id']

    # 2. Render focused editor block
    cat_options = {c["id"]: c["name"].title() for c in (cats or [])}
    opt_ids = list(cat_options.keys())
    _render_metric_editor_block(selected_metric, opt_ids, cat_options)

@st.fragment
def _render_metric_editor_block(m, opt_ids, cat_options):
    """Vertical-first editor block with integrated safety checks."""
    with st.container(border=True):
        if m.get('is_archived'):
            st.warning("⚠️ This metric is currently **Archived** and hidden from the dashboard.")
        
        new_name = st.text_input("Metric Name", value=m['name'], key=f"ed_nm_{m['id']}")
        new_desc = st.text_area("Description", value=m.get('description', ''), key=f"ed_desc_{m['id']}")
        
        col_unit, col_cat = st.columns(2)
        new_unit = col_unit.text_input("Unit", value=m.get('unit_name', ''), key=f"ed_un_{m['id']}")
        
        sorted_opt_ids = sorted(opt_ids, key=lambda x: cat_options.get(x, "").lower())
        select_opts = sorted_opt_ids + ["NEW_CAT"]
        
        new_cat_id = col_cat.selectbox(
            "Category", options=select_opts,
            format_func=lambda x: "✨ New..." if x == "NEW_CAT" else cat_options.get(x, "Uncat"),
            index=select_opts.index(m.get("category_id")) if m.get("category_id") in select_opts else 0,
            key=f"ed_ct_{m['id']}"
        )

        inline_cat_name = None
        if new_cat_id == "NEW_CAT":
            inline_cat_name = st.text_input("New Category Name", key=f"inline_cat_{m['id']}")

        current_kind = _infer_metric_kind(m)
        entry_count = models.get_entry_count(m["id"])
        can_change_kind = entry_count == 0
        kind_disabled_msg = None if can_change_kind else f"Kind locked (has {entry_count} entries). Use Convert below."

        kind_label = "Kind"
        if kind_disabled_msg:
            kind_label = f"{kind_label} — {kind_disabled_msg}"

        kind_key = f"ed_kind_{m['id']}"
        if kind_key not in st.session_state:
            st.session_state[kind_key] = current_kind

        new_kind = st.selectbox(
            kind_label,
            options=_METRIC_KIND_OPTIONS,
            index=_METRIC_KIND_OPTIONS.index(current_kind),
            key=kind_key,
            disabled=not can_change_kind,
        )

        if not can_change_kind:
            col_conv, _ = st.columns([1, 2])
            if col_conv.button("Convert…", key=f"conv_btn_{m['id']}", use_container_width=True):
                _convert_metric_kind_dialog(m)

        new_higher_is_better = bool(m.get("higher_is_better", True))
        if new_kind == "score":
            new_higher_is_better = st.toggle(
                "Higher is better",
                value=new_higher_is_better,
                key=f"ed_hib_{m['id']}",
            )

        new_start, new_end = m.get("range_start", 0), m.get("range_end", 10)
        range_error = False
        error_msg = ""
        
        if new_kind == "score":
            rcol1, rcol2 = st.columns(2)
            new_start = rcol1.number_input(
                "Min",
                value=_int_or_default(m.get("range_start"), 1),
                step=1,
                key=f"rs_{m['id']}",
            )
            new_end = rcol2.number_input(
                "Max",
                value=_int_or_default(m.get("range_end"), 5),
                step=1,
                key=f"re_{m['id']}",
            )
            
            if new_start >= new_end:
                range_error, error_msg = True, "Max must be strictly greater than Min."

            if not range_error:
                actual_min, actual_max = models.get_metric_value_bounds(m['id'])
                if actual_min is not None:
                    if new_start > actual_min:
                        range_error, error_msg = True, f"Existing data has values as low as {actual_min}."
                    elif new_end < actual_max:
                        range_error, error_msg = True, f"Existing data has values as high as {actual_max}."

        if range_error:
            st.error(error_msg)

        # Action row: safe or archive
        st.divider()
        col_save, col_arch = st.columns([2, 1])

        with col_save:
            if st.button("💾 Save Changes", key=f"upd_sv_{m['id']}", type="primary", use_container_width=True, disabled=range_error):
                target_cat_id = utils.ensure_category_id(new_cat_id, inline_cat_name)
                
                payload = {
                    "name": utils.normalize_name(new_name),
                    "description": new_desc.strip() if new_desc else None, #
                    "unit_name": utils.normalize_name(new_unit),
                    "category_id": target_cat_id
                }
                if new_kind == "score":
                    payload["range_start"], payload["range_end"] = new_start, new_end
                    payload["higher_is_better"] = bool(new_higher_is_better)

                if can_change_kind:
                    payload["metric_kind"] = new_kind
                    payload["unit_type"] = _KIND_TO_UNIT_TYPE[new_kind]

                # Triggers the dialog to show full Current vs Proposed changes
                _confirm_metric_update_dialog(
                    m,
                    payload,
                    cat_options=cat_options,
                    new_cat_name=inline_cat_name
                )

        with col_arch:
            is_archived = m.get('is_archived', False)
            
            if not is_archived:
                # Show Archive button if metric is active
                if st.button("📦 Archive", key=f"arch_{m['id']}", help="Hide from dashboard", use_container_width=True):
                    models.archive_metric(m['id'])
                    utils.finalize_action(f"Archived: {m['name'].title()}", icon="📦")
                    st.rerun()
            else:
                # Show Restore button if metric is already archived
                if st.button("♻️ Restore", key=f"rest_{m['id']}", help="Show on dashboard again", use_container_width=True):
                    # You'll need this simple function in models.py: 
                    # sb.table("metrics").update({"is_archived": False}).eq("id", m['id'])
                    models.update_metric(m['id'], {"is_archived": False})
                    utils.finalize_action(f"Restored: {m['name'].title()}", icon="✅")
                    st.rerun()

def show_create_metric(cats):
    """
    Mobile-optimized metric creation.
    Replaces the collapsed expander with a dedicated, focused layout.
    """
    st.subheader("Define New Metric")
    
    with st.container(border=True):
        # 1. Basic Metadata
        mn = st.text_input("Metric Name", placeholder="e.g., Daily Steps", key="create_mn")

        # 1.5 Add Description Field
        desc = st.text_area("Description (Optional)", placeholder="What does this metric track?", key="create_desc")

        col_unit, col_kind = st.columns(2)
        unit_name = col_unit.text_input("Unit", placeholder="e.g., km", key="create_unit")
        metric_kind = col_kind.selectbox(
            "Kind",
            options=_METRIC_KIND_OPTIONS,
            format_func=lambda k: {"quantitative": "Quantitative", "count": "Count", "score": "Score"}.get(k, k),
            key="create_mkind",
        )
        unit_type = _KIND_TO_UNIT_TYPE[metric_kind]

        # 2. Dynamic Range Configuration
        range_start, range_end = 0, 10
        range_error = False
        higher_is_better = True
        if metric_kind == "score":
            higher_is_better = st.toggle("Higher is better", value=True, key="create_hib")
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min Value", value=1, step=1, key="create_rs")
            range_end = rcol2.number_input("Max Value", value=5, step=1, key="create_re")
            if range_start >= range_end:
                st.error("Max must be greater than Min")
                range_error = True

        # 3. Category Assignment
        sorted_cats = sorted(cats, key=lambda x: x["name"].lower()) if cats else []
        cat_opts = (
            [(None, "— none —")] + 
            [(c["id"], c["name"].title()) for c in sorted_cats] + 
            [("NEW_CAT", "✨ Create New...")]
        )
        
        cat_choice = st.selectbox(
            "Assign Category", 
            [o[0] for o in cat_opts], 
            format_func=lambda i: next((n for (_id, n) in cat_opts if _id == i), "— none —"),
            key="create_cat"
        )
        
        new_cat_name = None
        if cat_choice == "NEW_CAT":
            new_cat_name = st.text_input("New Category Name", key="create_new_cat_name")

        # 4. Vertical Primary Action
        st.markdown("<div style='padding-top: 10px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 Create Metric", type="primary", use_container_width=True, disabled=range_error):
            if mn.strip():
                final_cat_id = utils.ensure_category_id(cat_choice, new_cat_name)
                
                payload = {
                    "name": utils.normalize_name(mn), 
                    "description": desc.strip() if desc else None,
                    "unit_name": utils.normalize_name(unit_name) if unit_name else None,
                    "unit_type": unit_type, 
                    "metric_kind": metric_kind,
                    "category_id": final_cat_id
                }
                
                if metric_kind == "score":
                    payload["range_start"] = range_start
                    payload["range_end"] = range_end
                    payload["higher_is_better"] = bool(higher_is_better)

                models.create_metric(payload)
                
                # Centralized feedback and refresh
                utils.finalize_action(f"Created: {mn.strip().title()}")
            else:
                st.warning("Please enter a name for the metric.")

def select_metric(metrics, target_id=None):
    if not metrics:
        return None
    
    sorted_metrics = sorted(
        metrics,
        key=lambda x: (bool(x.get("is_archived")), x.get("name", "").lower()),
    )
    id_to_metric = {m["id"]: m for m in sorted_metrics}

    categories = models.get_categories() or []
    cat_labels = {c["id"]: c.get("name", "").title() for c in categories}
    
    active_id = target_id or st.session_state.get("last_active_mid")
    selected_obj = next((m for m in sorted_metrics if str(m['id']) == str(active_id)), None)
    
    if not selected_obj:
        selected_obj = next((m for m in sorted_metrics if not m.get("is_archived")), None)
        if not selected_obj:
            selected_obj = sorted_metrics[0]
        st.session_state["last_active_mid"] = selected_obj['id']

    with st.container(border=True):
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown(f"**🎯 {utils.format_metric_label(selected_obj)}**")
        with c_right:
            if st.button("Browse…", use_container_width=True):
                _browse_metric_dialog(sorted_metrics, cat_labels, selected_obj["id"])

    return selected_obj
