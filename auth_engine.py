import streamlit as st
from supabase_config import sb

class AuthEngine:
    @staticmethod
    def normalize_input(text):
        """Standardizes input and handles iOS smart punctuation for stability."""
        if not text: return ""
        replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '--', '–': '-'}
        for s, r in replacements.items():
            text = text.replace(s, r)
        return text.strip()

    @staticmethod
    def sign_in(email, password):
        try:
            email_clean = email.strip().lower()
            pwd_clean = AuthEngine.normalize_input(password)
            res = sb.auth.sign_in_with_password({"email": email_clean, "password": pwd_clean})
            return res.user, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def sign_up(email, password):
        try:
            res = sb.auth.sign_up({"email": email, "password": password})
            return res.user, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def update_password(new_password):
        """Updates password and kills recovery session to ensure no stale state."""
        try:
            clean_pwd = AuthEngine.normalize_input(new_password)
            sb.auth.update_user({"password": clean_pwd})
            sb.auth.sign_out() 
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def request_reset(email):
        try:
            url = st.secrets.get("REDIRECT_URL", "http://localhost:8501").strip()
            sb.auth.reset_password_for_email(email, {"redirect_to": url})
            return True, None
        except Exception as e:
            return False, str(e)