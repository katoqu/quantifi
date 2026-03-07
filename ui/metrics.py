"""Main metrics UI module - orchestrates metric management components."""

import streamlit as st
import models
import utils
from .metrics_dialogs import (
    _metric_search_label,
    show_browse_metric_dialog,
    _infer_metric_kind,
    _can_convert_kind,
    _metric_matches_query,
    _int_or_default,
)
from .metrics_editor import show_edit_metrics
from .metrics_create import show_create_metric


def select_metric(metrics, target_id=None):
    """Display metric selector with browse functionality."""
    if not metrics:
        return None
    
    sorted_metrics = sorted(
        metrics,
        key=lambda x: (bool(x.get("is_archived")), x.get("name", "").lower()),
    )

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
                show_browse_metric_dialog(sorted_metrics, cat_labels, selected_obj["id"])

    return selected_obj
