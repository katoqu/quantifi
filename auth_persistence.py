import base64
import json
from typing import Any

import streamlit as st


COOKIE_NAME = "quantifi_auth"
_CM_KEY = "_quantifi_cookie_manager"


def _cookies_enabled() -> bool:
    raw = st.secrets.get("PERSIST_LOGIN", True)
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}


def _cookie_manager():
    """
    Returns an `extra_streamlit_components.CookieManager` instance, or None if the
    dependency isn't installed.
    """
    try:
        import extra_streamlit_components as stx  # type: ignore
    except Exception:
        return None

    if _CM_KEY not in st.session_state:
        st.session_state[_CM_KEY] = stx.CookieManager()
    return st.session_state[_CM_KEY]


def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":"), ensure_ascii=False).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")


def _decode(value: str) -> dict[str, Any] | None:
    try:
        raw = base64.urlsafe_b64decode((value or "").encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None


def load() -> str | dict[str, Any] | None:
    """
    Loads persisted auth material from a browser cookie.

    Returns one of:
    - `sid` (str): the opaque server-side session id (preferred)
    - legacy payload (dict): contains `access_token` + `refresh_token` (migration only)
    - None
    """
    if not _cookies_enabled():
        return None
    cm = _cookie_manager()
    if cm is None:
        return None
    value = cm.get(COOKIE_NAME)
    if not value:
        return None

    decoded = _decode(value)
    if isinstance(decoded, dict):
        if isinstance(decoded.get("sid"), str) and decoded["sid"].strip():
            return decoded["sid"].strip()
        if decoded.get("access_token") and decoded.get("refresh_token"):
            return decoded
    # Support storing raw SID strings too.
    return str(value).strip()


def save_sid(sid: str, *, max_age_days: int = 30) -> bool:
    if not _cookies_enabled():
        return False
    cm = _cookie_manager()
    if cm is None:
        return False
    cm.set(COOKIE_NAME, _encode({"sid": sid}), expires_at_days=max_age_days)
    return True


def clear() -> bool:
    if not _cookies_enabled():
        return False
    cm = _cookie_manager()
    if cm is None:
        return False
    cm.delete(COOKIE_NAME)
    return True
