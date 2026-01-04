import streamlit as st
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine

def init_session_state():
    """Initializes the session state and synchronizes with Supabase auth."""
    defaults = {
        "user": None, 
        "show_password_reset": False, 
        "show_recovery_form": False,
        "show_debug_panel": False,
        "auth_debug": []
    }
    for k, v in defaults.items():
        if k not in st.session_state: 
            st.session_state[k] = v

    # Check if we already have a user in session; if not, check Supabase
    if st.session_state.user is None:
        try:
            res = sb.auth.get_user()
            if res and res.user: 
                st.session_state.user = res.user
                # Clear cache on initial load if a user is found to ensure 
                # their specific metrics are loaded, not the public/empty ones.
                if "initial_load_done" not in st.session_state:
                    st.cache_data.clear()
                    st.session_state.initial_load_done = True 
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

def sign_out():
    """Signs out the user, clears all cached data, and resets the session."""
    try:
        sb.auth.sign_out()
    except Exception as e:
        st.session_state.auth_debug.append(f"Sign out error: {str(e)}")
    
    # 1. Clear session state user
    st.session_state.user = None
    
    # 2. IMPORTANT: Clear global cache so the next user doesn't see old data
    st.cache_data.clear() 
    
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
            sb.auth.verify_otp({"token_hash": params["token_hash"], "type": params["type"]})
            st.session_state.show_recovery_form = True
            st.query_params.clear()
            st.cache_data.clear() # Clear cache as auth context has changed
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
        t1, t2 = st.tabs(["Sign In", "Sign Up"])
        with t1: 
            AuthUI.render_login_tab()
        with t2: 
            AuthUI.render_signup_tab()