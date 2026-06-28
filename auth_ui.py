import streamlit as st
import time
from auth_engine import AuthEngine
import cache_control
import auth_persistence

class AuthUI:
    @staticmethod
    def _secrets_truthy(value) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def _handle_login():
        """Callback to process login before the page re-renders."""
        st.session_state.login_error = None
        email = st.session_state.get("auth_login_email", "")
        pwd = st.session_state.get("auth_login_password", "")
        
        user, session, err = AuthEngine.sign_in(email, pwd)
        
        if user:
            access_token = None
            refresh_token = None
            if session:
                if isinstance(session, dict):
                    access_token = session.get("access_token")
                    refresh_token = session.get("refresh_token")
                else:
                    access_token = getattr(session, "access_token", None)
                    refresh_token = getattr(session, "refresh_token", None)
            
            if access_token and refresh_token:
                auth_persistence.save_tokens(access_token, refresh_token)
            else:
                payload = AuthEngine.get_session_payload()
                if payload and payload.get("access_token") and payload.get("refresh_token"):
                    auth_persistence.save_tokens(payload["access_token"], payload["refresh_token"])

            cache_control.bump()
            st.session_state.user = user
            st.session_state.login_error = None
        else:
            st.session_state.login_error = err

    @staticmethod
    def _handle_signup():
        """Callback to process signups before the page re-renders."""
        st.session_state.signup_error = None
        email = st.session_state.get("auth_signup_email", "")
        pwd = st.session_state.get("auth_signup_password", "")
        
        user, session, err = AuthEngine.sign_up(email, pwd)
        
        if user:
            access_token = None
            refresh_token = None
            if session:
                if isinstance(session, dict):
                    access_token = session.get("access_token")
                    refresh_token = session.get("refresh_token")
                else:
                    access_token = getattr(session, "access_token", None)
                    refresh_token = getattr(session, "refresh_token", None)
            
            if access_token and refresh_token:
                auth_persistence.save_tokens(access_token, refresh_token)
            else:
                payload = AuthEngine.get_session_payload()
                if payload and payload.get("access_token") and payload.get("refresh_token"):
                    auth_persistence.save_tokens(payload["access_token"], payload["refresh_token"])

            cache_control.bump()
            st.session_state.user = user
            st.session_state.signup_error = None
        else:
            st.session_state.signup_error = err

    @staticmethod
    def render_login_tab():
        st.subheader("Sign In")

        email = st.text_input("Email", key="auth_login_email")

        with st.form("password_login_form", border=False):
            pwd = st.text_input("Password", type="password", key="auth_login_password")
            st.form_submit_button("Sign in", use_container_width=True, type="primary", on_click=AuthUI._handle_login)
            
        if st.session_state.get("login_error"):
            if not st.session_state.get("user"):
                st.error(f"Login failed: {st.session_state.login_error}")
            st.session_state.login_error = None

        if st.button("Forgot password?", type="secondary"):
            st.session_state.show_password_reset = True
            st.rerun()

    @staticmethod
    def render_signup_tab():
        st.subheader("Create an Account")
        email = st.text_input("Email", key="auth_signup_email")

        if AuthEngine.allowlist_enabled():
            verified_email = st.session_state.get("allowlist_verified_email")
            email_clean = (email or "").strip().lower()
            if verified_email != email_clean:
                st.session_state.allowlist_verified_email = None

            if st.button("Continue", type="primary", use_container_width=True):
                ok, err = AuthEngine.is_email_allowlisted(email)
                if ok:
                    st.session_state.allowlist_verified_email = email_clean
                    st.session_state.signup_error = None
                else:
                    st.session_state.signup_error = err or "This email is not approved yet."

            if st.session_state.get("allowlist_verified_email") != email_clean:
                st.caption("Only approved emails can create accounts.")
            else:
                with st.form("password_signup_form_verified", border=False):
                    pwd = st.text_input(
                        "Password",
                        type="password",
                        key="auth_signup_password_verified",
                    )
                    st.form_submit_button(
                        "Sign up",
                        use_container_width=True,
                        type="primary",
                        on_click=AuthUI._handle_signup,
                    )
        else:
            with st.form("password_signup_form", border=False):
                pwd = st.text_input("Password", type="password", key="auth_signup_password")
                st.form_submit_button("Sign up", use_container_width=True, type="primary", on_click=AuthUI._handle_signup)
            
        if st.session_state.get("signup_error"):
            if not st.session_state.get("user"):
                st.error(f"Sign up failed: {st.session_state.signup_error}")
            st.session_state.signup_error = None

    @staticmethod
    @staticmethod
    def render_recovery_form():
        recovery_type = str(st.session_state.get("recovery_type") or "").strip().lower()
        st.title("Set New Password")
        with st.container(border=True):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            button_label = "Update password"
            if st.button(button_label, type="primary", use_container_width=True):
                if new_p == conf_p and new_p:
                    success, err = AuthEngine.update_password(new_p)
                    if success:
                        cache_control.bump()
                        st.success("Updated! Redirecting to login...")
                        st.query_params.clear()
                        st.session_state.show_recovery_form = False
                        st.session_state.recovery_type = None
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
