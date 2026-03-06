from __future__ import annotations

from dataclasses import dataclass
from typing import Literal, Mapping

MissingPolicy = Literal["ignore_missing", "missing_is_zero"]
DailyAgg = Literal["sum", "mean", "last", "max", "min"]


@dataclass(frozen=True)
class MetricPolicy:
    missing_policy: MissingPolicy = "ignore_missing"
    daily_agg: DailyAgg = "sum"


DEFAULT_POLICY = MetricPolicy()


POLICY_BY_METRIC_NAME: Mapping[str, MetricPolicy] = {
    # Example:
    # "yoga": MetricPolicy(missing_policy="missing_is_zero"),
}

_SS_MISSING_IS_ZERO_PREFIX = "metric_missing_is_zero::"


def _try_get_session_state() -> dict | None:
    try:
        import streamlit as st  # type: ignore
    except Exception:
        return None
    try:
        return st.session_state  # type: ignore[no-any-return]
    except Exception:
        return None


def _metric_key(metric_name: str | None, metric_id: str | None) -> str:
    if metric_id:
        return str(metric_id)
    return (metric_name or "").strip().lower()


def set_missing_is_zero_override(*, metric_name: str | None = None, metric_id: str | None = None, enabled: bool) -> None:
    ss = _try_get_session_state()
    if ss is None:
        return
    key = _metric_key(metric_name, metric_id)
    if not key:
        return
    ss[_SS_MISSING_IS_ZERO_PREFIX + key] = bool(enabled)


def get_missing_is_zero_override(*, metric_name: str | None = None, metric_id: str | None = None) -> bool | None:
    ss = _try_get_session_state()
    if ss is None:
        return None
    key = _metric_key(metric_name, metric_id)
    if not key:
        return None
    v = ss.get(_SS_MISSING_IS_ZERO_PREFIX + key)
    if v is None:
        return None
    return bool(v)


def resolve_metric_policy(metric_name: str | None, *, metric_id: str | None = None) -> MetricPolicy:
    name_key = (metric_name or "").strip().lower()
    base = POLICY_BY_METRIC_NAME.get(name_key, DEFAULT_POLICY)

    override = get_missing_is_zero_override(metric_name=metric_name, metric_id=metric_id)
    if override is None:
        return base
    missing_policy: MissingPolicy = "missing_is_zero" if override else "ignore_missing"
    if base.missing_policy == missing_policy:
        return base
    return MetricPolicy(missing_policy=missing_policy, daily_agg=base.daily_agg)


# TODO: Persist `missing_policy` (and later `daily_agg`) on the `metrics` table so this setting
# survives across sessions/devices. Migration path:
# - Add columns `missing_policy` and `daily_agg` with sensible defaults.
# - Read those fields into the metric dict from Supabase.
# - Update `resolve_metric_policy()` to prefer DB values over session overrides, and add a UI control
#   in the metric settings (⚙️) to update the DB.
