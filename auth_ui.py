import streamlit as st
import time
from urllib.parse import quote
from auth_engine import AuthEngine

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
            "Hi,\n\nCould I get an invite to QuantifI?\n\nMy email:\n\nThanks!"
        )
        mailto = f"mailto:{to}?subject={subject}&body={body}"
        st.link_button("Request access", mailto, use_container_width=True)

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
        
        if AuthUI._invite_only_enabled():
            AuthUI._render_request_access()

        if st.button("Forgot Password?", type="secondary", icon="🔑"):
            st.session_state.show_password_reset = True
            st.rerun()

    @staticmethod
    def render_signup_tab():
        if AuthUI._invite_only_enabled():
            st.info("Invite-only access is enabled. Ask an admin for an invite.")
            return

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
        is_invite = st.session_state.get("recovery_type") == "invite"
        st.title("Set Password" if is_invite else "Set New Password")
        with st.container(border=True):
            new_p = st.text_input("New Password", type="password")
            conf_p = st.text_input("Confirm Password", type="password")
            btn_label = "Accept Invite" if is_invite else "Update and Sign In"
            if st.button(btn_label, type="primary", use_container_width=True):
                if new_p == conf_p and new_p:
                    success, err = AuthEngine.update_password(new_p)
                    if success:
                        # --- FIX: Clear cache on successful recovery/login ---
                        st.cache_data.clear() 
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
