import streamlit as st
from supabase_config import sb, sb_admin

class AuthEngine:
    @staticmethod
    def _secrets_truthy(value) -> bool:
        if value is None:
            return False
        if isinstance(value, bool):
            return value
        return str(value).strip().lower() in {"1", "true", "yes", "y", "on"}

    @staticmethod
    def normalize_input(text):
        """Standardizes input and handles iOS smart punctuation for stability."""
        if not text: 
            return ""
        # Fixes common mobile input issues (e.g., smart quotes and dashes)
        replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '--', '–': '-'}
        for s, r in replacements.items():
            text = text.replace(s, r)
        return text.strip()

    @staticmethod
    def sign_in(email, password):
        """Authenticates with Supabase using PKCE-compatible flows."""
        try:
            email_clean = email.strip().lower()
            pwd_clean = AuthEngine.normalize_input(password)
            # pkce flow is handled by the client options in supabase_config
            res = sb.auth.sign_in_with_password({"email": email_clean, "password": pwd_clean})
            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            return user, session, None
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def sign_up(email, password):
        """Creates a new user account with normalized credentials."""
        if AuthEngine._secrets_truthy(st.secrets.get("INVITE_ONLY", False)):
            return None, None, "Sign-ups are disabled. Ask an admin for an invite."
        try:
            email_clean = email.strip().lower()
            pwd_clean = AuthEngine.normalize_input(password)
            res = sb.auth.sign_up({"email": email_clean, "password": pwd_clean})
            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            return user, session, None
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def update_password(new_password):
        """Updates password and clears the session for a clean re-login."""
        try:
            clean_pwd = AuthEngine.normalize_input(new_password)
            sb.auth.update_user({"password": clean_pwd})
            # Ensures no lingering recovery tokens remain active
            sb.auth.sign_out() 
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def request_reset(email):
        """Sends a password recovery email using the configured redirect URL."""
        try:
            # Fetches redirect URL from secrets; vital for PKCE redirect stability
            url = st.secrets.get("REDIRECT_URL", "http://localhost:8501").strip()
            sb.auth.reset_password_for_email(email.strip(), {"redirect_to": url})
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def invite_user(email):
        """
        Sends a Supabase Auth invite email (admin-only).

        Note: this is different from Streamlit Community Cloud app sharing invites.
        """
        try:
            email_clean = (email or "").strip().lower()
            if not email_clean:
                return False, "Email is required."
            url = st.secrets.get("REDIRECT_URL", "http://localhost:8501").strip()
            sb_admin.auth.admin.invite_user_by_email(email_clean, {"redirect_to": url})
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def session_to_payload(session) -> dict | None:
        """
        Normalizes a Supabase session object to a JSON-serializable payload for cookies.
        """
        if session is None:
            return None
        if isinstance(session, dict):
            access_token = session.get("access_token")
            refresh_token = session.get("refresh_token")
            expires_at = session.get("expires_at")
        else:
            access_token = getattr(session, "access_token", None)
            refresh_token = getattr(session, "refresh_token", None)
            expires_at = getattr(session, "expires_at", None)
        if not access_token or not refresh_token:
            return None
        payload: dict = {"access_token": access_token, "refresh_token": refresh_token}
        if expires_at is not None:
            payload["expires_at"] = expires_at
        return payload

    @staticmethod
    def restore_session(access_token: str, refresh_token: str):
        """
        Restores a Supabase session (best-effort) from tokens.
        Returns (user, session, err).
        """
        try:
            if hasattr(sb.auth, "set_session"):
                res = sb.auth.set_session(access_token, refresh_token)
            elif hasattr(sb.auth, "recover_session"):
                # Older gotrue client variants
                res = sb.auth.recover_session(access_token)
            else:
                return None, None, "Supabase auth client does not support session restore."

            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            if isinstance(res, dict):
                user = res.get("user") or user
                session = res.get("session") or session
            return user, session, None
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def maybe_refresh_session(seconds_skew: int = 120):
        """
        Refreshes the Supabase session if it is close to expiry (best-effort).
        Returns (session, err) where session may be None when no refresh happened.
        """
        try:
            get_session = getattr(sb.auth, "get_session", None)
            if not callable(get_session):
                return None, None
            sess = get_session()
            session = getattr(sess, "session", None) if sess else None
            if session is None and isinstance(sess, dict):
                session = sess.get("session")
            if session is None:
                return None, None

            expires_at = getattr(session, "expires_at", None)
            if expires_at is None and isinstance(session, dict):
                expires_at = session.get("expires_at")
            if not expires_at:
                return None, None

            import time

            if int(expires_at) - int(time.time()) > int(seconds_skew):
                return None, None

            refresh = getattr(sb.auth, "refresh_session", None)
            if callable(refresh):
                res = refresh()
                new_session = getattr(res, "session", None) if res else None
                if new_session is None and isinstance(res, dict):
                    new_session = res.get("session")
                return new_session, None
            return None, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_session_payload():
        """
        Best-effort accessor for current session tokens (for SID store refresh/migration).
        """
        try:
            get_session = getattr(sb.auth, "get_session", None)
            if not callable(get_session):
                return None
            sess = get_session()
            session = getattr(sess, "session", None) if sess else None
            if session is None and isinstance(sess, dict):
                session = sess.get("session")
            return AuthEngine.session_to_payload(session)
        except Exception:
            return None
