import streamlit as st
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine
import auth_persistence
import cache_control
import session_store

def _secrets_truthy(value) -> bool:
    if value is None:
        return False
    if isinstance(value, bool):
        return value
    return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

def is_invite_only() -> bool:
    return _secrets_truthy(st.secrets.get("INVITE_ONLY", False))

def init_session_state():
    """Initializes the session state and synchronizes with Supabase auth."""
    defaults = {
        "user": None, 
        "show_password_reset": False, 
        "show_recovery_form": False,
        "recovery_type": None,
        "show_debug_panel": False,
        "auth_debug": [],
        "use_time_sticky": False,          # Fixes the 'no key' error
        "tracker_view_selector": "Overview", # Ensures smooth tab switching
        "last_active_mid": None,           # For 'sticky' metric selection
        "active_cat_filter": "All",        # For landing page filtering
        "cache_buster": 0,                 # Per-session cache invalidation key
        "auth_sid": None,                  # Opaque server-side session id
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v

    # Best-effort: keep session alive if we're close to expiry.
    if st.session_state.user is not None:
        new_session, err = AuthEngine.maybe_refresh_session()
        if err:
            st.session_state.auth_debug.append(f"Session refresh error: {err}")
        payload = AuthEngine.session_to_payload(new_session)
        if payload and session_store.enabled() and st.session_state.get("auth_sid"):
            try:
                session_store.update_session(sid=str(st.session_state.get("auth_sid")), session_payload=payload)
            except Exception as e:
                st.session_state.auth_debug.append(f"Session store update error: {e}")

    # Check if we already have a user in session; if not, attempt restore.
    if st.session_state.user is None:
        persisted = auth_persistence.load()

        # 1) Preferred: opaque SID cookie -> encrypted tokens in Supabase.
        if isinstance(persisted, str) and persisted and session_store.enabled():
            sid = persisted
            payload = None
            try:
                payload = session_store.load_session_payload(sid)
            except Exception as e:
                st.session_state.auth_debug.append(f"Session store load error: {e}")

            if payload and payload.get("access_token") and payload.get("refresh_token"):
                user, new_session, err = AuthEngine.restore_session(
                    payload["access_token"], payload["refresh_token"]
                )
                if user:
                    st.session_state.user = user
                    st.session_state["auth_sid"] = sid
                    cache_control.bump()
                    return
                if err:
                    st.session_state.auth_debug.append(f"SID restore failed: {err}")
            # If SID was invalid, clear it.
            auth_persistence.clear()
            st.session_state["auth_sid"] = None

        # 2) Migration: legacy token cookie -> convert to SID store (if enabled).
        if isinstance(persisted, dict) and session_store.enabled():
            if persisted.get("access_token") and persisted.get("refresh_token"):
                user, new_session, err = AuthEngine.restore_session(
                    persisted["access_token"], persisted["refresh_token"]
                )
                if user:
                    st.session_state.user = user
                    payload = AuthEngine.session_to_payload(new_session) or persisted
                    try:
                        sid = session_store.create_session(
                            user_id=str(getattr(user, "id", "")), session_payload=payload
                        )
                        if sid:
                            st.session_state["auth_sid"] = sid
                            auth_persistence.save_sid(sid)
                    except Exception as e:
                        st.session_state.auth_debug.append(f"Legacy migration store error: {e}")
                    cache_control.bump()
                    return
                if err:
                    st.session_state.auth_debug.append(f"Legacy cookie restore failed: {err}")
            auth_persistence.clear()

        # 2) Fallback: in-memory Supabase auth state (same Streamlit session).
        try:
            res = sb.auth.get_user()
            user = getattr(res, "user", None) if res else None
            if user:
                st.session_state.user = user
                # If we can, persist this session as an opaque SID for future restarts.
                if session_store.enabled() and not st.session_state.get("auth_sid"):
                    payload = AuthEngine.get_session_payload()
                    if payload:
                        try:
                            sid = session_store.create_session(
                                user_id=str(getattr(user, "id", "")), session_payload=payload
                            )
                            if sid:
                                st.session_state["auth_sid"] = sid
                                auth_persistence.save_sid(sid)
                        except Exception as e:
                            st.session_state.auth_debug.append(f"Fallback SID store error: {e}")
        except Exception as e:
            st.session_state.auth_debug.append(f"Session init error: {str(e)}")

def is_authenticated():
    """Returns True if a user is logged in and not currently recovering an account."""
    if st.session_state.get("show_recovery_form"):
        return False
    return st.session_state.get("user") is not None

def get_current_user():
    """Safely retrieves the current user object."""
    return st.session_state.get("user")

def _get_admin_emails() -> set[str]:
    raw = (st.secrets.get("ADMIN_EMAILS", "") or "").strip()
    if not raw:
        return set()
    return {e.strip().lower() for e in raw.split(",") if e.strip()}

def is_admin() -> bool:
    user = get_current_user()
    if not user or not getattr(user, "email", None):
        return False
    admins = _get_admin_emails()
    if not admins:
        return False
    return user.email.strip().lower() in admins

def sign_out():
    """Signs out the user, clears all cached data, and resets the session."""
    try:
        sb.auth.sign_out()
    except Exception as e:
        st.session_state.auth_debug.append(f"Sign out error: {str(e)}")

    if session_store.enabled() and st.session_state.get("auth_sid"):
        try:
            session_store.revoke_session(str(st.session_state.get("auth_sid")))
        except Exception as e:
            st.session_state.auth_debug.append(f"Revoke SID error: {e}")

    auth_persistence.clear()
    
    # 1. Clear session state user
    st.session_state.user = None
    st.session_state["auth_sid"] = None
    
    # 2. Invalidate per-session caches so the next view starts fresh.
    cache_control.bump()
    
    # 3. Clean up UI states
    st.session_state.show_recovery_form = False
    st.session_state.show_password_reset = False
    
    st.rerun()

def auth_page():
    """Renders the authentication interface and handles deep-link tokens."""
    # 1. Handle Link Tokens (Password recovery / Email verification)
    params = st.query_params
    if "token_hash" in params and "type" in params:
        try:
            token_type = str(params["type"]).strip()
            res = sb.auth.verify_otp({"token_hash": params["token_hash"], "type": token_type})

            st.query_params.clear()
            cache_control.bump()  # Auth context changed

            # Only recovery/invite flows should prompt for a new password.
            if token_type in ("recovery", "invite"):
                st.session_state.recovery_type = token_type
                st.session_state.show_recovery_form = True
            else:
                st.session_state.recovery_type = None
                st.session_state.show_recovery_form = False
                user = getattr(res, "user", None) if res else None
                session = getattr(res, "session", None) if res else None
                if isinstance(res, dict):
                    user = res.get("user") or user
                    session = res.get("session") or session
                if user:
                    st.session_state.user = user
                payload = AuthEngine.session_to_payload(session)
                if payload and user and session_store.enabled():
                    sid = session_store.create_session(
                        user_id=str(getattr(user, "id", "")), session_payload=payload
                    )
                    if sid:
                        st.session_state["auth_sid"] = sid
                        auth_persistence.save_sid(sid)
                st.rerun()
        except Exception as e:
            st.error(f"Link invalid or expired: {e}")

    # 2. Debug Panel
    AuthUI.render_debug_panel()

    # 3. Routing logic based on session state
    if st.session_state.show_recovery_form:
        AuthUI.render_recovery_form()
    
    elif st.session_state.show_password_reset:
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
            AuthUI.render_login_tab()
        else:
            t1, t2 = st.tabs(["Sign In", "Sign Up"])
            with t1:
                AuthUI.render_login_tab()
            with t2:
                AuthUI.render_signup_tab()
