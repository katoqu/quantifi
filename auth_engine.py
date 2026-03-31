import time
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
        replacements = {'“': '"', '”': '"', '‘': "'", '’': "'", '—': '--', '–': '-'}
        for s, r in replacements.items():
            text = text.replace(s, r)
        return text.strip()

    @staticmethod
    def _with_retries(func, retries=3, delay=1.0):
        """
        Executes a network function with retries to handle mobile wake-up latency.
        Waits `delay` seconds between attempts if a transient network error occurs.
        """
        last_err = None
        # Ensure we always try at least once
        actual_retries = max(1, retries) 
        
        for attempt in range(actual_retries):
            try:
                return func()
            except Exception as e:
                last_err = e
                err_str = str(e).lower()
                # If Supabase explicitly rejects the token, do not retry.
                # Only retry on network timeouts, connection drops, etc.
                if "invalid" in err_str or "expired" in err_str:
                    raise e
                time.sleep(delay)
                
        # Safely raise the error only if it's an actual exception
        if last_err is not None:
            raise last_err
        else:
            raise RuntimeError("Network operation failed unexpectedly.")

    @staticmethod
    def allowlist_enabled() -> bool:
        return AuthEngine._secrets_truthy(st.secrets.get("SIGNUP_ALLOWLIST_ENABLED", False))

    @staticmethod
    def _allowlist_table() -> str:
        raw = (st.secrets.get("SIGNUP_ALLOWLIST_TABLE", "") or "").strip()
        return raw or "signup_allowlist"

    @staticmethod
    def is_email_allowlisted(email: str):
        try:
            if not AuthEngine.allowlist_enabled():
                return True, None
            email_clean = (email or "").strip().lower()
            if not email_clean:
                return False, "Email is required."
            table = AuthEngine._allowlist_table()
            res = sb_admin.table(table).select("email").eq("email", email_clean).limit(1).execute()
            data = getattr(res, "data", None) if res else None
            if isinstance(res, dict):
                data = res.get("data") or data
            return bool(data), None if data else "This email is not approved yet."
        except Exception as e:
            return False, str(e)

    @staticmethod
    def add_allowlist_email(email: str):
        try:
            email_clean = (email or "").strip().lower()
            if not email_clean:
                return False, "Email is required."
            table = AuthEngine._allowlist_table()
            payload = {"email": email_clean}
            # Prefer upsert to avoid duplicate errors where supported.
            try:
                sb_admin.table(table).upsert(payload, on_conflict="email").execute()
            except Exception:
                sb_admin.table(table).insert(payload).execute()
            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def sign_in(email, password):
        try:
            email_clean = email.strip().lower()
            pwd_clean = AuthEngine.normalize_input(password)
            res = sb.auth.sign_in_with_password({"email": email_clean, "password": pwd_clean})
            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            return user, session, None
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def send_magic_link(email: str):
        try:
            email_clean = (email or "").strip().lower()
            if not email_clean:
                return False, "Email is required."

            url = st.secrets.get("REDIRECT_URL", "http://localhost:8501").strip()
            fn = getattr(sb.auth, "sign_in_with_otp", None)
            if not callable(fn):
                return False, "Supabase client does not support OTP/magic links."

            attempts = [
                {"email": email_clean, "options": {"email_redirect_to": url}},
                {"email": email_clean, "email_redirect_to": url},
                {"email": email_clean, "options": {"redirect_to": url}},
                {"email": email_clean, "redirect_to": url},
            ]
            last_err: Exception | None = None
            for payload in attempts:
                try:
                    fn(payload)
                    last_err = None
                    break
                except TypeError as e:
                    last_err = e
                    continue
                except Exception as e:
                    last_err = e
                    continue
            if last_err is not None:
                raise last_err

            return True, None
        except Exception as e:
            return False, str(e)

    @staticmethod
    def sign_up(email, password):
        if AuthEngine.allowlist_enabled():
            ok, err = AuthEngine.is_email_allowlisted(email)
            if not ok:
                return None, None, err or "This email is not approved yet."
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
            sb.auth.reset_password_for_email(email.strip(), {"redirect_to": url})
            return True, None
        except Exception as e:
            return False, str(e)


    @staticmethod
    def exchange_code_for_session(code: str):
        """
        Exchanges a PKCE auth code for a session (used by magic link flows).
        Tries multiple payload shapes to stay compatible across supabase-py versions.
        """
        try:
            code_clean = (code or "").strip()
            if not code_clean:
                return None, None, "Missing auth code."

            fn = getattr(sb.auth, "exchange_code_for_session", None)
            if not callable(fn):
                return None, None, "Supabase client does not support code exchange."

            attempts = [
                {"auth_code": code_clean},
                {"code": code_clean},
                code_clean,
            ]
            last_err: Exception | None = None
            res = None
            for payload in attempts:
                try:
                    res = fn(payload)
                    last_err = None
                    break
                except TypeError as e:
                    last_err = e
                    continue
                except Exception as e:
                    last_err = e
                    continue
            if last_err is not None:
                raise last_err

            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            if isinstance(res, dict):
                user = res.get("user") or user
                session = res.get("session") or session
            return user, session, None
        except Exception as e:
            return None, None, str(e)

    @staticmethod
    def session_to_payload(session) -> dict | None:
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
        try:
            if hasattr(sb.auth, "set_session"):
                # Use our new retry wrapper to survive mobile wake-ups
                res = AuthEngine._with_retries(lambda: sb.auth.set_session(access_token, refresh_token))
            elif hasattr(sb.auth, "recover_session"):
                res = AuthEngine._with_retries(lambda: sb.auth.recover_session(access_token))
            else:
                return None, None, "Supabase auth client does not support session restore."

            user = getattr(res, "user", None) if res else None
            session = getattr(res, "session", None) if res else None
            if isinstance(res, dict):
                user = res.get("user") or user
                session = res.get("session") or session
            return user, session, None
            
        except Exception as e:
            try:
                refresh = getattr(sb.auth, "refresh_session", None)
                if callable(refresh):
                    # Use our new retry wrapper here too
                    def _do_refresh():
                        try:
                            return refresh(refresh_token)
                        except TypeError:
                            return refresh()
                    
                    refreshed = AuthEngine._with_retries(_do_refresh)
                    
                    new_session = getattr(refreshed, "session", None) if refreshed else None
                    if new_session is None and isinstance(refreshed, dict):
                        new_session = refreshed.get("session")
                    payload = AuthEngine.session_to_payload(new_session)
                    if payload and hasattr(sb.auth, "set_session"):
                        res = AuthEngine._with_retries(lambda: sb.auth.set_session(payload["access_token"], payload["refresh_token"]))
                        user = getattr(res, "user", None) if res else None
                        session = getattr(res, "session", None) if res else None
                        if isinstance(res, dict):
                            user = res.get("user") or user
                            session = res.get("session") or session
                        return user, session, None
            except Exception:
                pass

            return None, None, str(e)

    @staticmethod
    def maybe_refresh_session(seconds_skew: int = 120):
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
                # Apply retry wrapper to the proactive refresh
                res = AuthEngine._with_retries(lambda: refresh())
                new_session = getattr(res, "session", None) if res else None
                if new_session is None and isinstance(res, dict):
                    new_session = res.get("session")
                return new_session, None
            return None, None
        except Exception as e:
            return None, str(e)

    @staticmethod
    def get_session_payload():
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
