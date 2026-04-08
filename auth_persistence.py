import datetime
import base64
import json
import uuid
from typing import Any
import streamlit as st
import session_store

# Constants
COOKIE_NAME = "quantifi_auth"
_CM_KEY = "_quantifi_cookie_manager"

def _cookie_manager():
    """
    Returns a stable extra_streamlit_components.CookieManager instance.
    Stored in session_state to remain future-proof against caching deprecations.
    """
    try:
        import extra_streamlit_components as stx  # type: ignore
    except ImportError:
        return None

    # Initialize once per session using a strict key
    if _CM_KEY not in st.session_state:
        st.session_state[_CM_KEY] = stx.CookieManager(key="quantifi_cm_widget")
        
    return st.session_state[_CM_KEY]

def _cookies_enabled() -> bool:
    raw = st.secrets.get("PERSIST_LOGIN", True)
    if raw is None:
        return False
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in {"1", "true", "yes", "y", "on"}

def mount():
    """Forces the CookieManager component to render on the current page."""
    if _cookies_enabled():
        cm = _cookie_manager()
        if cm is not None:
            # Calling get_all() forces the HTML/JS to inject into the DOM
            cm.get_all()

def _encode(payload: dict[str, Any]) -> str:
    raw = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    return base64.urlsafe_b64encode(raw).decode("ascii")

def _decode(value: str) -> dict[str, Any] | None:
    try:
        val_str = str(value or "")
        # Restore missing padding lost in browser transit
        missing_padding = len(val_str) % 4
        if missing_padding:
            val_str += "=" * (4 - missing_padding)
            
        raw = base64.urlsafe_b64decode(val_str.encode("ascii"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except Exception:
        return None

def _session_store_enabled() -> bool:
    try:
        return session_store.enabled()
    except Exception:
        return False

def _read_cookie_value() -> str | None:
    if not _cookies_enabled():
        return None
    cm = _cookie_manager()
    if cm is None:
        return None
    value = cm.get(COOKIE_NAME)
    return str(value) if value else None

def _extract_sid(value: str | None) -> str | None:
    if not value:
        return None
    decoded = _decode(value)
    if isinstance(decoded, dict):
        sid = decoded.get("sid")
        if isinstance(sid, str) and sid:
            return sid
    # If cookie is raw SID, accept UUID-ish values.
    try:
        sid = str(value).strip()
        if not sid:
            return None
        uuid.UUID(sid)
        return sid
    except Exception:
        return None

def load() -> dict[str, str] | None:
    """Loads persisted Supabase access and refresh tokens from the browser cookie."""
    if not _cookies_enabled():
        return None
    value = _read_cookie_value()
    if not value:
        return None

    # Preferred: server-side session store with SID cookie.
    if _session_store_enabled():
        sid = _extract_sid(value)
        if sid:
            try:
                payload = session_store.load_session_payload(sid)
                if isinstance(payload, dict) and payload.get("access_token") and payload.get("refresh_token"):
                    return payload
            except Exception:
                pass

    # Legacy fallback: tokens stored directly in cookie.
    decoded = _decode(value)
    if isinstance(decoded, dict) and decoded.get("access_token") and decoded.get("refresh_token"):
        return decoded
    return None

def save_tokens(access_token: str, refresh_token: str, max_age_days: int = 30) -> bool:
    """Saves the Supabase tokens to the browser cookie."""
    if not _cookies_enabled():
        return False
    cm = _cookie_manager()
    if cm is None:
        return False
        
    payload = {"access_token": access_token, "refresh_token": refresh_token}
    expiration_date = datetime.datetime.now() + datetime.timedelta(days=max_age_days)

    # Preferred: store tokens server-side and persist only SID in cookie.
    if _session_store_enabled():
        try:
            existing_sid = _extract_sid(_read_cookie_value())
            if existing_sid:
                if session_store.update_session(sid=existing_sid, session_payload=payload):
                    cm.set(COOKIE_NAME, _encode({"sid": existing_sid}), expires_at=expiration_date)
                    return True
            user = st.session_state.get("user")
            user_id = getattr(user, "id", None) if user is not None else None
            if not user_id:
                user_id = "unknown"
            sid = session_store.create_session(
                user_id=str(user_id),
                session_payload=payload,
                max_age_days=max_age_days,
            )
            if sid:
                cm.set(COOKIE_NAME, _encode({"sid": sid}), expires_at=expiration_date)
                return True
        except Exception:
            # Fall back to legacy cookie storage if server-side persistence fails.
            pass

    cm.set(COOKIE_NAME, _encode(payload), expires_at=expiration_date)
    return True

def clear() -> bool:
    """Removes the authentication cookie."""
    if not _cookies_enabled():
        return False
    cm = _cookie_manager()
    if cm is None:
        return False
        
    try:
        if _session_store_enabled():
            sid = _extract_sid(_read_cookie_value())
            if sid:
                try:
                    session_store.revoke_session(sid)
                except Exception:
                    pass
        cm.delete(COOKIE_NAME)
    except KeyError:
        pass 
    return True
