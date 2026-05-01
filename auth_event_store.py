import datetime
from typing import Any

import streamlit as st

from supabase_config import sb_admin


def _secrets_truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}


def enabled() -> bool:
    return _secrets_truthy(st.secrets.get("AUTH_EVENT_LOG_DB", False))


def _table_name() -> str:
    raw = (st.secrets.get("AUTH_EVENT_LOG_TABLE", "") or "").strip()
    return raw or "auth_event_logs"


def _env_name() -> str:
    raw = (st.secrets.get("ENV_NAME", "") or "").strip()
    return raw or "unknown"


def write_event(*, event: str, payload: dict[str, Any], user_id: str | None = None, sid: str | None = None) -> None:
    """
    Persists token-safe auth diagnostics into Supabase for durable production analysis.
    """
    if not enabled():
        return

    row = {
        "created_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
        "env": _env_name(),
        "event": str(event or "").strip() or "unknown",
        "user_id": user_id,
        "sid": sid,
        "payload": payload,
    }
    sb_admin.table(_table_name()).insert(row).execute()

