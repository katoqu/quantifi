import streamlit as st
from supabase_config import sb
from auth_ui import AuthUI
from auth_engine import AuthEngine

def init_session_state():
    defaults = {
        "user": None, 
        "show_password_reset": False, 
        "show_recovery_form": False,
        "show_debug_panel": False,
        "auth_debug": []
    }
    for k, v in defaults.items():
        if k not in st.session_state: st.session_state[k] = v

    if st.session_state.user is None:
        try:
            res = sb.auth.get_user()
            if res and res.user: st.session_state.user = res.user
        except: pass

def is_authenticated():
    if st.session_state.get("show_recovery_form"):
        return False
    return st.session_state.get("user") is not None

def get_current_user():
    return st.session_state.get("user")

def sign_out():
    sb.auth.sign_out()
    st.session_state.user = None
    st.rerun()

def auth_page():
    # 1. Handle Link Tokens
    params = st.query_params
    if "token_hash" in params and "type" in params:
        try:
            sb.auth.verify_otp({"token_hash": params["token_hash"], "type": params["type"]})
            st.session_state.show_recovery_form = True
            st.query_params.clear()
        except Exception as e:
            st.error(f"Link invalid or expired: {e}")

    # 2. Page Routing
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
                if success: st.success("Sent!")
                else: st.error(err)
        with col2:
            if st.button("Back"):
                st.session_state.show_password_reset = False
                st.rerun()
    else:
        st.title("QuantifI")
        t1, t2 = st.tabs(["Sign In", "Sign Up"])
        with t1: AuthUI.render_login_tab()
        with t2: AuthUI.render_signup_tab()