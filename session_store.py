import json
import time
import uuid
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
    """
    Returns True if secure server-side session persistence is enabled.

    Requires:
    - `PERSIST_LOGIN` truthy (default: True)
    - `SESSION_ENC_KEY` set (Fernet key)
    - `SUPABASE_SERVICE_ROLE_KEY` set (for server-side session table access)
    """
    if not _secrets_truthy(st.secrets.get("PERSIST_LOGIN", True)):
        return False
    if not (st.secrets.get("SESSION_ENC_KEY") or "").strip():
        return False
    if not (st.secrets.get("SUPABASE_SERVICE_ROLE_KEY") or "").strip():
        return False
    return True


def _fernet():
    from cryptography.fernet import Fernet  # local import to keep import-time light

    key = (st.secrets.get("SESSION_ENC_KEY") or "").strip()
    if not key:
        raise RuntimeError("Missing SESSION_ENC_KEY")
    return Fernet(key.encode("utf-8"))


def _encrypt(payload: dict[str, Any]) -> str:
    token = _fernet().encrypt(json.dumps(payload, separators=(",", ":")).encode("utf-8"))
    return token.decode("utf-8")


def _decrypt(token_blob: str) -> dict[str, Any] | None:
    from cryptography.fernet import InvalidToken  # type: ignore

    try:
        raw = _fernet().decrypt((token_blob or "").encode("utf-8"))
        data = json.loads(raw.decode("utf-8"))
        return data if isinstance(data, dict) else None
    except (InvalidToken, ValueError, TypeError):
        return None


def create_session(*, user_id: str, session_payload: dict[str, Any], max_age_days: int = 30) -> str | None:
    """
    Stores encrypted Supabase tokens server-side and returns an opaque SID.
    """
    if not enabled():
        return None

    sid = str(uuid.uuid4())
    now = int(time.time())
    blob = _encrypt(session_payload)
    res = (
        sb_admin.table("app_sessions")
        .insert(
            {
                "id": sid,
                "user_id": user_id,
                "token_blob": blob,
                "created_at": now,
                "last_seen_at": now,
                "max_age_days": int(max_age_days),
            }
        )
        .execute()
    )
    _ = res  # best-effort; errors will raise via supabase client
    return sid


def update_session(*, sid: str, session_payload: dict[str, Any]) -> bool:
    if not enabled():
        return False
    now = int(time.time())
    blob = _encrypt(session_payload)
    (
        sb_admin.table("app_sessions")
        .update({"token_blob": blob, "last_seen_at": now})
        .eq("id", sid)
        .is_("revoked_at", "null")
        .execute()
    )
    return True


def revoke_session(sid: str) -> bool:
    if not enabled():
        return False
    now = int(time.time())
    (
        sb_admin.table("app_sessions")
        .update({"revoked_at": now})
        .eq("id", sid)
        .is_("revoked_at", "null")
        .execute()
    )
    return True


def load_session_payload(sid: str) -> dict[str, Any] | None:
    """
    Loads and decrypts the token payload for a given SID. Returns None if missing/revoked/invalid.
    """
    if not enabled():
        return None
    if not sid:
        return None

    res = (
        sb_admin.table("app_sessions")
        .select("token_blob,revoked_at,max_age_days,created_at")
        .eq("id", sid)
        .limit(1)
        .execute()
    )
    rows = getattr(res, "data", None) or []
    if not rows:
        return None
    row = rows[0] or {}
    if row.get("revoked_at") is not None:
        return None

    created_at = int(row.get("created_at") or 0)
    max_age_days = int(row.get("max_age_days") or 30)
    if created_at > 0:
        age_seconds = int(time.time()) - created_at
        if age_seconds > max_age_days * 86400:
            revoke_session(sid)
            return None

    blob = row.get("token_blob") or ""
    payload = _decrypt(blob)
    if not payload:
        return None

    # Touch last-seen (best-effort)
    try:
        sb_admin.table("app_sessions").update({"last_seen_at": int(time.time())}).eq("id", sid).execute()
    except Exception:
        pass

    return payload

