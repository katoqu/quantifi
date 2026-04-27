import streamlit as st
try:  # pragma: no cover - defensive for tests without full Streamlit
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover
    components = None
import datetime
import json
import os
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine
import auth_persistence
import cache_control
import time

def _admin_emails() -> list[str]:
    raw = (st.secrets.get("ADMIN_EMAILS", "") or "").strip()
    if not raw:
        return []
    emails = [e.strip().lower() for e in raw.split(",") if e.strip()]
    # preserve order but de-dupe
    seen = set()
    out = []
    for e in emails:
        if e not in seen:
            seen.add(e)
            out.append(e)
    return out

def _persist_session_tokens(session):
    payload = AuthEngine.session_to_payload(session)
    if payload and payload.get("access_token") and payload.get("refresh_token"):
        auth_persistence.save_tokens(payload["access_token"], payload["refresh_token"])

def _refresh_skew_seconds() -> int:
    raw = st.secrets.get("AUTH_REFRESH_SKEW_SECONDS", 1800)
    try:
        val = int(raw)
    except Exception:
        return 1800
    if val < 60:
        return 60
    return val

def _persist_current_session_tokens():
    payload = AuthEngine.get_session_payload()
    if payload and payload.get("access_token") and payload.get("refresh_token"):
        auth_persistence.save_tokens(payload["access_token"], payload["refresh_token"])

def _append_auth_debug(message: str):
    debug_log = st.session_state.get("auth_debug")
    if not isinstance(debug_log, list):
        debug_log = []
        st.session_state["auth_debug"] = debug_log
    debug_log.append(message)
    max_items = 400
    if len(debug_log) > max_items:
        del debug_log[0 : len(debug_log) - max_items]

def _auth_log_enabled() -> bool:
    raw = st.secrets.get("AUTH_EVENT_LOG", True)
    return AuthEngine._secrets_truthy(raw)

def _auth_log_path() -> str:
    raw = str(st.secrets.get("AUTH_EVENT_LOG_PATH", "logs/auth_events.jsonl") or "").strip()
    return raw or "logs/auth_events.jsonl"

def _json_safe(value):
    if value is None:
        return None
    if isinstance(value, (bool, int, float)):
        return value
    if isinstance(value, str):
        return value if len(value) <= 240 else f"{value[:240]}..."
    if isinstance(value, dict):
        return {str(k): _json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_safe(v) for v in value]
    return str(value)

def _auth_event(event: str, **fields):
    ts = datetime.datetime.now(datetime.timezone.utc).isoformat()
    payload = {"ts": ts, "event": event}
    for key, value in fields.items():
        payload[key] = _json_safe(value)
    _append_auth_debug(f"[{event}] {json.dumps(payload, separators=(',', ':'), ensure_ascii=True)}")
    if not _auth_log_enabled():
        return
    try:
        path = _auth_log_path()
        folder = os.path.dirname(path)
        if folder:
            os.makedirs(folder, exist_ok=True)
        with open(path, "a", encoding="utf-8") as f:
            f.write(json.dumps(payload, separators=(",", ":"), ensure_ascii=True) + "\n")
    except Exception as e:
        _append_auth_debug(f"Auth event log write failed: {e}")

def _error_kind(err: str | None) -> str:
    text = str(err or "").strip().lower()
    if not text:
        return "none"
    if "invalid" in text or "expired" in text:
        return "invalid_or_expired"
    if (
        "timeout" in text
        or "connection" in text
        or "network" in text
        or "temporar" in text
        or "unavailable" in text
        or "dns" in text
    ):
        return "transient_network"
    return "other_error"

def _cookie_retry_limit() -> int:
    raw = st.secrets.get("AUTH_COOKIE_RESTORE_RETRIES", 2)
    try:
        val = int(raw)
    except Exception:
        return 2
    if val < 0:
        return 0
    if val > 8:
        return 8
    return val

def _cookie_retry_delay_seconds() -> float:
    raw = st.secrets.get("AUTH_COOKIE_RESTORE_DELAY_SECONDS", 0.5)
    try:
        val = float(raw)
    except Exception:
        return 0.5
    if val < 0.05:
        return 0.05
    if val > 3.0:
        return 3.0
    return val

def init_session_state():
    """Initializes session state with a persistence bridge for mobile wake-ups."""
    
    auth_persistence.mount()

    # 1. Define Defaults
    defaults = {
        "user": None, 
        "auth_debug": [],
        "tracker_view_selector": "Home",   
        "cache_buster": 0,
        "_logout_pending": False,
        "_restore_attempts": 0,  # Safety counter for mobile wake-ups
        "app_just_woke_up": True, 
        "_cookie_restore_failed": False,
        "show_recovery_form": False,
        "show_password_reset": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v
    _auth_event(
        "init_session_state",
        user_present=bool(st.session_state.get("user")),
        restore_attempts=int(st.session_state.get("_restore_attempts", 0)),
    )

    # 2. Proactive Refresh (For users who are already logged in and active)
    if st.session_state.user is not None:
        # Keep cookie tokens in sync in case refresh token rotation happened.
        _persist_current_session_tokens()
        # Proactively refresh before expiry.
        new_session, err = AuthEngine.maybe_refresh_session(
            seconds_skew=_refresh_skew_seconds()
        )
        if new_session:
            payload = AuthEngine.session_to_payload(new_session)
            if payload:
                auth_persistence.save_tokens(payload["access_token"], payload["refresh_token"])
                _auth_event("proactive_refresh_ok")
        elif err:
            _auth_event("proactive_refresh_err", error_kind=_error_kind(err), error=err)
        return # Skip restore logic if user is already valid in memory

    # 3. Restore Logic (The 'Safety Bridge' for mobile wake-up)
    if st.session_state.user is None:
        persistence = auth_persistence.inspect_state()
        _auth_event("persistence_state", **persistence)
        persisted = auth_persistence.load()

        # If a cookie is found, attempt to restore the Supabase session
        if isinstance(persisted, dict) and persisted.get("access_token"):
            user, session, err = AuthEngine.restore_session(
                persisted["access_token"], persisted["refresh_token"]
            )
            if user:
                st.session_state.user = user
                st.session_state._restore_attempts = 0 # Success, reset counter
                st.session_state["_cookie_restore_failed"] = False
                _auth_event("cookie_restore_ok")
                return
            
            if err:
                err_kind = _error_kind(err)
                _auth_event("cookie_restore_err", error_kind=err_kind, error=err)
                if err_kind == "transient_network":
                    st.session_state["_cookie_restore_failed"] = True

        # --- THE BRIDGE ---
        # If no cookie is found on the first try, the mobile browser is likely 
        # still waking up. Wait briefly and rerun a limited number of times.
        retry_limit = _cookie_retry_limit()
        if st.session_state._restore_attempts < retry_limit:
            st.session_state._restore_attempts += 1
            delay_s = _cookie_retry_delay_seconds()
            _auth_event(
                "cookie_retry_wait",
                retry_index=int(st.session_state._restore_attempts),
                retry_limit=retry_limit,
                delay_seconds=delay_s,
            )
            time.sleep(delay_s)
            st.rerun()

    # 4. Final Fallback: Check if Supabase client already has the user in memory
    try:
        res = sb.auth.get_user()
        user = getattr(res, "user", None) if res else None
        if user:
            st.session_state.user = user
            _auth_event("fallback_get_user_ok")
    except Exception as e:
        _auth_event("fallback_get_user_err", error=str(e))

def is_authenticated():
    if st.session_state.get("show_recovery_form"):
        return False
    return st.session_state.get("user") is not None

def get_current_user():
    return st.session_state.get("user")

def is_admin() -> bool:
    user = get_current_user()
    if not user or not getattr(user, "email", None):
        return False
    admins = set(_admin_emails())
    if not admins:
        return False
    return user.email.strip().lower() in admins

def sign_out():
    try:
        sb.auth.sign_out()
    except Exception as e:
        _auth_event("sign_out_err", error=str(e))

    auth_persistence.clear()
    st.session_state.user = None
    st.session_state["_logout_pending"] = True
    cache_control.bump()
    st.session_state.show_recovery_form = False
    st.session_state.show_password_reset = False
    _auth_event("sign_out_done")
    
def handle_link_tokens() -> bool:
    params = st.query_params
    token_type = str(params.get("type", "")).strip().lower()

    if "access_token" in params and "refresh_token" in params:
        try:
            access = str(params.get("access_token", "")).strip()
            refresh = str(params.get("refresh_token", "")).strip()
            user, session, err = AuthEngine.restore_session(access, refresh)
            st.query_params.clear()
            cache_control.bump()
            if err:
                _auth_event("link_restore_err", error_kind=_error_kind(err), error=err)
                st.error(f"Link invalid or expired: {err}")
                return True

            if user:
                st.session_state.user = user
                _auth_event("link_restore_ok", flow="access_refresh")
            if session:
                _persist_session_tokens(session)

            if token_type == "recovery":
                st.session_state.recovery_type = "recovery"
                st.session_state.show_recovery_form = True
            else:
                st.session_state.recovery_type = None
                st.session_state.show_recovery_form = False
            return True
        except Exception as e:
            _auth_event("link_restore_exception", error=str(e))
            st.error(f"Link invalid or expired: {e}")
            return True

    if "code" in params:
        try:
            code = str(params["code"]).strip()
            user, session, err = AuthEngine.exchange_code_for_session(code)
            st.query_params.clear()
            cache_control.bump()
            if err:
                _auth_event("link_exchange_err", error_kind=_error_kind(err), error=err)
                st.error(f"Link invalid or expired: {err}")
                return True

            if user:
                st.session_state.user = user
                _auth_event("link_exchange_ok", flow="code")
            if session:
                _persist_session_tokens(session)

            if token_type == "recovery":
                st.session_state.recovery_type = "recovery"
                st.session_state.show_recovery_form = True
            else:
                st.session_state.recovery_type = None
                st.session_state.show_recovery_form = False

            return True
        except Exception as e:
            _auth_event("link_exchange_exception", error=str(e))
            st.error(f"Link invalid or expired: {e}")
            return True

    if "token_hash" not in params or "type" not in params:
        return False

    try:
        res = sb.auth.verify_otp({"token_hash": params["token_hash"], "type": token_type})
        st.query_params.clear()
        cache_control.bump() 

        if token_type == "recovery":
            st.session_state.recovery_type = "recovery"
            st.session_state.show_recovery_form = True
            return True

        st.session_state.recovery_type = None
        st.session_state.show_recovery_form = False

        user = getattr(res, "user", None) if res else None
        session = getattr(res, "session", None) if res else None
        if isinstance(res, dict):
            user = res.get("user") or user
            session = res.get("session") or session
        if user:
            st.session_state.user = user
        if session:
            _persist_session_tokens(session)
        _auth_event("link_verify_otp_ok", token_type=token_type)

        return True
    except Exception as e:
        _auth_event("link_verify_otp_exception", error=str(e))
        st.error(f"Link invalid or expired: {e}")
        return True

def auth_page():
    """Renders the authentication interface and handles deep-link tokens."""
    if components is not None:
        components.html(
            """
<script>
(function() {
  const target = (window.parent && window.parent.location) ? window.parent : (window.top && window.top.location ? window.top : window);
  const hash = target.location.hash || "";
  if (!hash || hash.length < 2) return;
  const hashParams = new URLSearchParams(hash.slice(1));
  if (!hashParams.get("access_token")) return;
  const qs = new URLSearchParams(target.location.search);
  if (qs.get("access_token")) return; // already bridged
  // If Supabase didn't include type in the redirect, try to recover it from the referrer.
  if (!hashParams.get("type") && !qs.get("type") && document.referrer) {
    try {
      const ref = new URL(document.referrer);
      const refType = ref.searchParams.get("type");
      if (refType) {
        qs.set("type", refType);
      }
    } catch (e) {}
  }
  hashParams.forEach((v, k) => qs.set(k, v));
  const newUrl = target.location.pathname + "?" + qs.toString();
  target.location.replace(newUrl);
})();
</script>
            """,
            height=0,
        )
    if handle_link_tokens():
        st.rerun()

    AuthUI.render_debug_panel()
    if AuthEngine._secrets_truthy(st.secrets.get("AUTH_DEBUG", False)):
        with st.expander("Auth Debug (Admin)", expanded=False):
            st.caption(f"Query param keys: {', '.join(list(st.query_params.keys())) or 'none'}")

    # --- NEW: The Wake-Up Buffer ---
    # If this is the very first render of a new session (like after waking up),
    # give the browser 1 second to send the authentication cookies to Python.
    if st.session_state.get("app_just_woke_up", True):
        st.session_state["app_just_woke_up"] = False
        _auth_event("wake_up_buffer")
        st.title("QuantifI")
        with st.spinner("Resuming session..."):
            import time
            time.sleep(1.0) 
        st.rerun()

    # --- Catch network blips gracefully ---
    if st.session_state.get("_cookie_restore_failed"):
        _auth_event("cookie_restore_failed_ui")
        st.title("QuantifI")
        st.warning("Connection lost while waking the app. Tap below to reconnect.")
        if st.button("🔄 Reconnect", use_container_width=True, type="primary"):
            st.session_state["_cookie_restore_failed"] = False
            _auth_event("cookie_restore_reconnect_clicked")
            st.rerun()
        return

    if st.session_state.get("show_recovery_form", False):
        AuthUI.render_recovery_form()
    
    elif st.session_state.get("show_password_reset", False):
        st.subheader("Reset Password")
        email = st.text_input("Enter your email")
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Send Reset Link", type="primary"):
                success, err = AuthEngine.request_reset(email)
                if success: 
                    st.success("Sent!")
                else: 
                    st.error(err)
        with col2:
            if st.button("Back"):
                st.session_state.show_password_reset = False
                st.rerun()
    
    else:
        st.title("QuantifI")
        # Render the tabbed interface for traditional authentication
        tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
        with tab1:
            AuthUI.render_login_tab()
        with tab2:
            AuthUI.render_signup_tab()
