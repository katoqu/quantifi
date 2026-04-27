"""Editor components for metric management."""

import streamlit as st
import models
import utils
from .metrics_dialogs import (
    _infer_metric_kind,
    _METRIC_KIND_OPTIONS,
    _KIND_TO_UNIT_TYPE,
    show_convert_metric_kind_dialog,
    show_confirm_metric_update_dialog,
    show_confirm_metric_delete_dialog,
    _int_or_default,
)


def show_edit_metrics(metrics_list, cats):
    """Focused Mobile Editor: Only shows the 'Active' metric for editing."""
    st.subheader("Edit Metric")
    
    # Import here to avoid circular imports
    from .metrics import select_metric
    
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
                show_convert_metric_kind_dialog(m)

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
                if actual_min is not None and actual_max is not None:
                    if new_start > actual_min:
                        range_error, error_msg = True, f"Existing data has values as low as {actual_min}."
                    elif new_end < actual_max:
                        range_error, error_msg = True, f"Existing data has values as high as {actual_max}."

        if range_error:
            st.error(error_msg)

        # Action row: safe or archive
        st.divider()
        col_save, col_arch, col_del = st.columns([2, 1, 1])

        with col_save:
            if st.button("💾 Save Changes", key=f"upd_sv_{m['id']}", type="primary", use_container_width=True, disabled=range_error):
                target_cat_id = utils.ensure_category_id(new_cat_id, inline_cat_name)
                
                payload = {
                    "name": utils.normalize_name(new_name or ""),
                    "description": new_desc.strip() if new_desc else None,
                    "unit_name": utils.normalize_name(new_unit or ""),
                    "category_id": target_cat_id
                }
                if new_kind == "score":
                    payload["range_start"], payload["range_end"] = new_start, new_end
                    payload["higher_is_better"] = bool(new_higher_is_better)

                if can_change_kind:
                    payload["metric_kind"] = new_kind
                    payload["unit_type"] = _KIND_TO_UNIT_TYPE[new_kind]

                # Triggers the dialog to show full Current vs Proposed changes
                show_confirm_metric_update_dialog(
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
                    models.update_metric(m['id'], {"is_archived": False})
                    utils.finalize_action(f"Restored: {m['name'].title()}", icon="✅")
                    st.rerun()

        with col_del:
            if st.button(
                "🗑️ Delete",
                key=f"del_{m['id']}",
                help="Permanently delete this metric and all related entries",
                use_container_width=True,
            ):
                show_confirm_metric_delete_dialog(m)
