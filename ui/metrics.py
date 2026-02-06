import streamlit as st
import models
import utils


_RECENT_METRICS_MAX = 8


def _push_recent_metric(metric_id, *, max_items=_RECENT_METRICS_MAX):
    if not metric_id:
        return
    recent_ids = st.session_state.get("recent_metric_ids")
    if not isinstance(recent_ids, list):
        recent_ids = []
    recent_ids = [rid for rid in recent_ids if str(rid) != str(metric_id)]
    recent_ids.insert(0, metric_id)
    st.session_state["recent_metric_ids"] = recent_ids[:max_items]


def _metric_search_label(metric, cat_labels):
    cat_id = metric.get("category_id")
    cat = "Uncat" if cat_id is None else cat_labels.get(cat_id, "Uncat")
    return f"{cat} • {utils.format_metric_label(metric)}"


@st.dialog("Browse metrics")
def _browse_metric_dialog(metrics, cat_labels, current_id):
    if "exclude_archived_metrics" not in st.session_state:
        st.session_state["exclude_archived_metrics"] = True

    hide_archived = st.checkbox("Hide archived", key="exclude_archived_metrics")

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

    selected_category = st.selectbox(
        "Category",
        options=category_options,
        format_func=lambda x: "All" if x == "ALL" else ("Uncat" if x == "UNCAT" else cat_labels.get(x, "Uncat")),
        index=0,
    )

    if selected_category == "ALL":
        filtered_metrics = visible_metrics
    elif selected_category == "UNCAT":
        filtered_metrics = [m for m in visible_metrics if m.get("category_id") is None]
    else:
        filtered_metrics = [m for m in visible_metrics if m.get("category_id") == selected_category]

    filtered_ids = [m["id"] for m in sorted(filtered_metrics, key=lambda m: m.get("name", "").lower())]
    if not filtered_ids:
        st.caption("No matching metrics.")
        return

    default_idx = filtered_ids.index(current_id) if current_id in filtered_ids else 0
    picked_id = st.selectbox(
        "Metric",
        options=filtered_ids,
        index=default_idx,
        format_func=lambda mid: _metric_search_label(id_to_metric[mid], cat_labels),
    )

    col_use, col_cancel = st.columns(2)
    if col_use.button("Use metric", type="primary", use_container_width=True):
        st.session_state["last_active_mid"] = picked_id
        _push_recent_metric(picked_id)
        st.rerun()
    col_cancel.button("Cancel", use_container_width=True)

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
    if m.get("unit_type") == "integer_range":
        if m.get("range_start") != new_payload.get("range_start") or \
           m.get("range_end") != new_payload.get("range_end"):
            changes.append({
                "label": "Range",
                "old": f"{m.get('range_start')} - {m.get('range_end')}",
                "new": f"{new_payload.get('range_start')} - {new_payload.get('range_end')}"
            })

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
        st.session_state[f"rs_{m['id']}"] = int(m.get("range_start", 0))
        st.session_state[f"re_{m['id']}"] = int(m.get("range_end", 10))
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

        new_start, new_end = m.get("range_start", 0), m.get("range_end", 10)
        range_error = False
        error_msg = ""
        
        if m.get("unit_type") == "integer_range":
            rcol1, rcol2 = st.columns(2)
            new_start = rcol1.number_input("Min", value=int(m.get("range_start", 0)), step=1, key=f"rs_{m['id']}")
            new_end = rcol2.number_input("Max", value=int(m.get("range_end", 10)), step=1, key=f"re_{m['id']}")
            
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
                if m.get("unit_type") == "integer_range":
                    payload["range_start"], payload["range_end"] = new_start, new_end

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

        col_unit, col_type = st.columns(2)
        unit_name = col_unit.text_input("Unit", placeholder="e.g., km", key="create_unit")
        unit_type = col_type.selectbox(
            "Value Type", 
            options=["float", "integer", "integer_range"],
            key="create_utype"
        )

        # 2. Dynamic Range Configuration
        range_start, range_end = 0, 10
        range_error = False
        if unit_type == "integer_range":
            rcol1, rcol2 = st.columns(2)
            range_start = rcol1.number_input("Min Value", value=0, step=1, key="create_rs")
            range_end = rcol2.number_input("Max Value", value=10, step=1, key="create_re")
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
                    "category_id": final_cat_id
                }
                
                if unit_type == "integer_range":
                    payload["range_start"] = range_start
                    payload["range_end"] = range_end

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

    # Seed recents (do not reorder unless the user explicitly selects)
    recent_ids = st.session_state.get("recent_metric_ids")
    if not isinstance(recent_ids, list) or not recent_ids:
        st.session_state["recent_metric_ids"] = [selected_obj["id"]]
    elif selected_obj["id"] not in recent_ids:
        st.session_state["recent_metric_ids"] = [selected_obj["id"], *recent_ids][: _RECENT_METRICS_MAX]

    available_ids = {m["id"] for m in sorted_metrics}
    recent_ids = [rid for rid in st.session_state.get("recent_metric_ids", []) if rid in available_ids]
    if selected_obj["id"] not in recent_ids:
        recent_ids.insert(0, selected_obj["id"])
    recent_ids = recent_ids[:_RECENT_METRICS_MAX]

    with st.container(border=True):
        c_left, c_right = st.columns([3, 1])
        with c_left:
            st.markdown(f"**🎯 {utils.format_metric_label(selected_obj)}**")
        with c_right:
            if st.button("Browse…", use_container_width=True):
                _browse_metric_dialog(sorted_metrics, cat_labels, selected_obj["id"])

        if len(recent_ids) > 1:
            recent_key = "metric_recent_selector"
            if recent_key in st.session_state and st.session_state[recent_key] not in recent_ids:
                st.session_state.pop(recent_key, None)

            picked_recent = st.segmented_control(
                "Recent",
                options=recent_ids,
                format_func=lambda mid: utils.format_metric_label(id_to_metric.get(mid, {"id": mid})),
                selection_mode="single",
                label_visibility="collapsed",
                default=selected_obj["id"],
                key=recent_key,
            )

            if picked_recent and str(picked_recent) != str(selected_obj["id"]):
                st.session_state["last_active_mid"] = picked_recent
                _push_recent_metric(picked_recent)
                selected_obj = next((m for m in sorted_metrics if str(m["id"]) == str(picked_recent)), selected_obj)

    return selected_obj
