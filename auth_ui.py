import streamlit as st
import time
from auth_engine import AuthEngine

class AuthUI:
    @staticmethod
    def render_login_tab():
        with st.form("login_form", border=False):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            if st.form_submit_button("Sign In", use_container_width=True):
                user, err = AuthEngine.sign_in(email, pwd)
                if user:
                    # --- FIX: Clear cache so user-specific data loads immediately ---
                    st.cache_data.clear() 
                    st.session_state.user = user
                    st.rerun()
                else:
                    st.error(f"Login failed: {err}")
        
        if st.button("Forgot Password?", type="secondary", icon="🔑"):
            st.session_state.show_password_reset = True
            st.rerun()

    @staticmethod
    def render_signup_tab():
        with st.form("signup_form", border=False):
            email = st.text_input("Email")
            pwd = st.text_input("Password", type="password")
            conf = st.text_input("Confirm Password", type="password")
            if st.form_submit_button("Create Account", use_container_width=True):
                if pwd == conf and pwd:
                    user, err = AuthEngine.sign_up(email, pwd)
                    if not err:
                        st.success("Account created! Please check your email for confirmation.")
                    else:
                        st.error(err)
                else:
                    st.error("Passwords do not match.")

    @staticmethod
    def render_recovery_form():
        st.title("Set New Password")
        with st.container(border=True):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            if st.button("Update and Sign In", type="primary", use_container_width=True):
                if new_p == conf_p and new_p:
                    success, err = AuthEngine.update_password(new_p)
                    if success:
                        # --- FIX: Clear cache on successful recovery/login ---
                        st.cache_data.clear() 
                        st.success("Updated! Redirecting to login...")
                        st.query_params.clear()
                        st.session_state.show_recovery_form = False
                        time.sleep(2)
                        st.rerun()
                    else:
                        st.error(err)
                else:
                    st.error("Passwords do not match.")

    @staticmethod
    def render_debug_panel():
        if st.session_state.get("show_debug_panel"):
            with st.expander("🛠 Auth Debug Logs", expanded=True):
                if not st.session_state.get("auth_debug"):
                    st.info("No logs captured.")
                else:
                    for log in reversed(st.session_state.auth_debug):
                        st.text(log)
                    if st.button("Clear History"):
                        st.session_state.auth_debug = []
                        st.rerun()