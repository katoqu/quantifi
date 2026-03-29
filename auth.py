import streamlit as st
try:  # pragma: no cover - defensive for tests without full Streamlit
    import streamlit.components.v1 as components
except Exception:  # pragma: no cover
    components = None
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine
import auth_persistence
import cache_control
import time

def is_invite_only() -> bool:
    return AuthEngine._secrets_truthy(st.secrets.get("INVITE_ONLY", False))

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
        "show_recovery_form": False,
        "show_password_reset": False,
        "auth_show_request_access": False,
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v

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
                st.session_state.auth_debug.append("Workout session refreshed proactively.")
        return # Skip restore logic if user is already valid in memory

    # 3. Restore Logic (The 'Safety Bridge' for mobile wake-up)
    if st.session_state.user is None:
        persisted = auth_persistence.load()

        # If a cookie is found, attempt to restore the Supabase session
        if isinstance(persisted, dict) and persisted.get("access_token"):
            user, session, err = AuthEngine.restore_session(
                persisted["access_token"], persisted["refresh_token"]
            )
            if user:
                st.session_state.user = user
                st.session_state._restore_attempts = 0 # Success, reset counter
                return
            
            if err:
                st.session_state.auth_debug.append(f"Cookie restore error: {err}")

        # --- THE BRIDGE ---
        # If no cookie is found on the first try, the mobile browser is likely 
        # still waking up. We wait 0.5 seconds and rerun ONCE to try again.
        if st.session_state._restore_attempts < 1:
            st.session_state._restore_attempts += 1
            time.sleep(0.5) 
            st.rerun()

    # 4. Final Fallback: Check if Supabase client already has the user in memory
    try:
        res = sb.auth.get_user()
        user = getattr(res, "user", None) if res else None
        if user:
            st.session_state.user = user
    except Exception as e:
        st.session_state.auth_debug.append(f"Client memory check failed: {e}")

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
    admins = set(AuthUI._admin_emails())
    if not admins:
        return False
    return user.email.strip().lower() in admins

def sign_out():
    try:
        sb.auth.sign_out()
    except Exception as e:
        st.session_state.auth_debug.append(f"Sign out error: {str(e)}")

    auth_persistence.clear()
    st.session_state.user = None
    st.session_state["_logout_pending"] = True
    cache_control.bump()
    st.session_state.show_recovery_form = False
    st.session_state.show_password_reset = False
    
def handle_link_tokens() -> bool:
    params = st.query_params
    token_type = str(params.get("type", "")).strip().lower()
    invite_only = is_invite_only()

    if "access_token" in params and "refresh_token" in params:
        try:
            access = str(params.get("access_token", "")).strip()
            refresh = str(params.get("refresh_token", "")).strip()
            user, session, err = AuthEngine.restore_session(access, refresh)
            st.query_params.clear()
            cache_control.bump()
            if err:
                st.error(f"Link invalid or expired: {err}")
                st.session_state.auth_show_request_access = True
                return True

            if user:
                st.session_state.user = user
            if session:
                _persist_session_tokens(session)

            if token_type in {"recovery", "invite"} or (invite_only and token_type == ""):
                st.session_state.recovery_type = token_type or "invite"
                st.session_state.show_recovery_form = True
                st.session_state.auth_show_request_access = False
            else:
                st.session_state.recovery_type = None
                st.session_state.show_recovery_form = False
                st.session_state.auth_show_request_access = False
            return True
        except Exception as e:
            st.error(f"Link invalid or expired: {e}")
            st.session_state.auth_show_request_access = True
            return True

    if "code" in params:
        try:
            code = str(params["code"]).strip()
            user, session, err = AuthEngine.exchange_code_for_session(code)
            st.query_params.clear()
            cache_control.bump()
            if err:
                st.error(f"Link invalid or expired: {err}")
                st.session_state.auth_show_request_access = True
                return True

            if user:
                st.session_state.user = user
            if session:
                _persist_session_tokens(session)

            if token_type in {"recovery", "invite"} or (invite_only and token_type == ""):
                st.session_state.recovery_type = token_type or "invite"
                st.session_state.show_recovery_form = True
                st.session_state.auth_show_request_access = False
            else:
                st.session_state.recovery_type = None
                st.session_state.show_recovery_form = False
                st.session_state.auth_show_request_access = False

            return True
        except Exception as e:
            st.error(f"Link invalid or expired: {e}")
            return True

    if "token_hash" not in params or "type" not in params:
        return False

    try:
        res = sb.auth.verify_otp({"token_hash": params["token_hash"], "type": token_type})
        st.query_params.clear()
        cache_control.bump() 

        if token_type in {"recovery", "invite"} or (invite_only and token_type == ""):
            st.session_state.recovery_type = token_type or "invite"
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
        st.session_state.auth_show_request_access = False

        return True
    except Exception as e:
        st.error(f"Link invalid or expired: {e}")
        st.session_state.auth_show_request_access = True
        return True

def auth_page():
    """Renders the authentication interface and handles deep-link tokens."""
    if components is not None:
        components.html(
            """
<script>
(function() {
  const hash = window.location.hash || "";
  if (!hash || hash.length < 2) return;
  const hashParams = new URLSearchParams(hash.slice(1));
  if (!hashParams.get("access_token")) return;
  const qs = new URLSearchParams(window.location.search);
  if (qs.get("access_token")) return; // already bridged
  hashParams.forEach((v, k) => qs.set(k, v));
  const newUrl = window.location.pathname + "?" + qs.toString();
  window.location.replace(newUrl);
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
        st.title("QuantifI")
        with st.spinner("Resuming session..."):
            import time
            time.sleep(1.0) 
        st.rerun()

    # --- Catch network blips gracefully ---
    if st.session_state.get("_cookie_restore_failed"):
        st.title("QuantifI")
        st.warning("Connection lost while waking the app. Tap below to reconnect.")
        if st.button("🔄 Reconnect", use_container_width=True, type="primary"):
            st.session_state["_cookie_restore_failed"] = False
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
        if is_invite_only():
            st.caption("Invite-only access is enabled. Ask an admin for an invite.")
            if st.session_state.get("auth_show_request_access"):
                st.info("Invite link invalid or expired. Request a new invite.")
                tab1, tab2 = st.tabs(["Request Access", "Sign In"])
                with tab1:
                    AuthUI.render_request_access_tab()
                with tab2:
                    AuthUI.render_login_tab()
            else:
                tab1, tab2 = st.tabs(["Sign In", "Request Access"])
                with tab1:
                    AuthUI.render_login_tab()
                with tab2:
                    AuthUI.render_request_access_tab()
            st.session_state.auth_show_request_access = False
        else:
            # Render the tabbed interface for traditional authentication
            tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
            with tab1:
                AuthUI.render_login_tab()
            with tab2:
                AuthUI.render_signup_tab()
