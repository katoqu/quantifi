import streamlit as st
import time
from urllib.parse import quote
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
    def _invite_only_enabled() -> bool:
        return AuthUI._secrets_truthy(st.secrets.get("INVITE_ONLY", False))

    @staticmethod
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

    @staticmethod
    def _render_request_access():
        admins = AuthUI._admin_emails()
        if not admins:
            st.caption("Invite-only is enabled. Ask an admin for an invite.")
            return

        to = ",".join(admins)
        subject = quote("QuantifI access request")
        body = quote(
            "Hi,\n\nCould I get an invite to QuantifI?\n\nThanks!"
        )
        mailto = f"mailto:{to}?subject={subject}&body={body}"
        st.link_button("Request access", mailto, use_container_width=True)

    @staticmethod
    def _handle_login():
        """Callback to process login before the page re-renders."""
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

            cache_control.bump()
            st.session_state.user = user
            st.session_state.login_error = None
        else:
            st.session_state.login_error = err

    @staticmethod
    def _handle_signup():
        """Callback to process signups before the page re-renders."""
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
            st.error(f"Login failed: {st.session_state.login_error}")
            st.session_state.login_error = None
        
        if AuthUI._invite_only_enabled():
            AuthUI._render_request_access()
        else:
            if st.button("Forgot password?", type="secondary"):
                st.session_state.show_password_reset = True
                st.rerun()

    @staticmethod
    def render_signup_tab():
        if AuthUI._invite_only_enabled():
            st.info("Invite-only access is enabled. Ask an admin for an invite.")
            AuthUI._render_request_access()
            return

        st.subheader("Create an Account")
        
        email = st.text_input("Email", key="auth_signup_email")
        
        with st.form("password_signup_form", border=False):
            pwd = st.text_input("Password", type="password", key="auth_signup_password")
            st.form_submit_button("Sign up", use_container_width=True, type="primary", on_click=AuthUI._handle_signup)
            
        if st.session_state.get("signup_error"):
            st.error(f"Sign up failed: {st.session_state.signup_error}")
            st.session_state.signup_error = None

    @staticmethod
    def render_recovery_form():
        recovery_type = str(st.session_state.get("recovery_type") or "").strip().lower()
        if recovery_type == "invite":
            st.title("Create Your Account")
        else:
            st.title("Set New Password")
        with st.container(border=True):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            button_label = "Create account" if recovery_type == "invite" else "Update password"
            if st.button(button_label, type="primary", use_container_width=True):
                if new_p == conf_p and new_p:
                    success, err = AuthEngine.update_password(new_p)
                    if success:
                        cache_control.bump()
                        if recovery_type == "invite":
                            st.success("Account created! Redirecting to login...")
                        else:
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
