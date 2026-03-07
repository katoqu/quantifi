import streamlit as st
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine
import auth_persistence
import cache_control

def is_invite_only() -> bool:
    return AuthEngine._secrets_truthy(st.secrets.get("INVITE_ONLY", False))

def init_session_state():
    """Initializes the session state and synchronizes with Supabase auth."""
    
    # Force the CookieManager component to render on every page rerun
    # This guarantees that queued saves from your login callback actually execute.
    auth_persistence.mount()

    defaults = {
        "user": None, 
        "show_password_reset": False, 
        "show_recovery_form": False,
        "recovery_type": None,
        "show_debug_panel": False,
        "auth_debug": [],
        "use_time_sticky": False,          
        "tracker_view_selector": "Home",   
        "last_active_mid": None,           
        "active_cat_filter": "All",        
        "cache_buster": 0,
        "_logout_pending": False,          # Ensures clean logouts by ignoring stale cookies
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v

    # Best-effort: keep session alive if we're close to expiry.
    if st.session_state.user is not None:
        new_session, err = AuthEngine.maybe_refresh_session()
        if err:
            st.session_state.auth_debug.append(f"Session refresh error: {err}")

    # Check if we already have a user in session; if not, attempt restore.
    if st.session_state.user is None:
        persisted = auth_persistence.load()

        # Robust Zombie Cookie Shield
        if st.session_state.get("_logout_pending"):
            if persisted:
                # The frontend hasn't processed the cookie deletion yet. Keep the shield up.
                return
            else:
                # The cookie is confirmed deleted. Drop the shield.
                st.session_state["_logout_pending"] = False
                return

        # Restore from token cookie directly
        if isinstance(persisted, dict) and persisted.get("access_token") and persisted.get("refresh_token"):
            user, new_session, err = AuthEngine.restore_session(
                persisted["access_token"], persisted["refresh_token"]
            )
            if user:
                st.session_state.user = user
                cache_control.bump()
                return
            if err:
                st.session_state.auth_debug.append(f"Cookie restore failed: {err}")
            auth_persistence.clear()

        # Fallback: in-memory Supabase auth state
        try:
            res = sb.auth.get_user()
            user = getattr(res, "user", None) if res else None
            if user:
                st.session_state.user = user
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

def is_admin() -> bool:
    user = get_current_user()
    if not user or not getattr(user, "email", None):
        return False
    admins = set(AuthUI._admin_emails())
    if not admins:
        return False
    return user.email.strip().lower() in admins

def sign_out():
    """Signs out the user, clears all cached data, and resets the session."""
    try:
        sb.auth.sign_out()
    except Exception as e:
        st.session_state.auth_debug.append(f"Sign out error: {str(e)}")

    # Queues the cookie for deletion
    auth_persistence.clear()
    
    # Clear session state user and put up the zombie shield
    st.session_state.user = None
    st.session_state["_logout_pending"] = True

    # Invalidate per-session caches and clean up UI states
    cache_control.bump()
    st.session_state.show_recovery_form = False
    st.session_state.show_password_reset = False
    
def handle_link_tokens() -> bool:
    """Handles Supabase email deep-link tokens. Returns True if a token was processed."""
    params = st.query_params
    if "token_hash" not in params or "type" not in params:
        return False

    try:
        token_type = str(params["type"]).strip()
        res = sb.auth.verify_otp({"token_hash": params["token_hash"], "type": token_type})

        # Clear query params so refreshes don't re-process the token.
        st.query_params.clear()
        cache_control.bump() 

        if token_type == "recovery":
            st.session_state.recovery_type = token_type
            st.session_state.show_recovery_form = True
            return True

        st.session_state.recovery_type = None
        st.session_state.show_recovery_form = False

        user = getattr(res, "user", None) if res else None
        if isinstance(res, dict):
            user = res.get("user") or user
        if user:
            st.session_state.user = user

        return True
    except Exception as e:
        st.error(f"Link invalid or expired: {e}")
        return True

def auth_page():
    """Renders the authentication interface and handles deep-link tokens."""
    if handle_link_tokens():
        st.rerun()

    AuthUI.render_debug_panel()

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
            # Render the tabbed interface for traditional authentication
            tab1, tab2 = st.tabs(["Sign In", "Sign Up"])
            with tab1:
                AuthUI.render_login_tab()
            with tab2:
                AuthUI.render_signup_tab()