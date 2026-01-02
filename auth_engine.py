import streamlit as st
from supabase_config import sb

class AuthEngine:
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
            return res.user, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def sign_up(email, password):
        """Creates a new user account with normalized credentials."""
        try:
            email_clean = email.strip().lower()
            pwd_clean = AuthEngine.normalize_input(password)
            res = sb.auth.sign_up({"email": email_clean, "password": pwd_clean})
            return res.user, None
        except Exception as e:
            return None, str(e)

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