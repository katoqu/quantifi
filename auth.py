import streamlit as st
from supabase import ClientOptions, create_client
import time
from urllib.parse import urlparse, parse_qs
from supabase_config import sb

def init_session_state():
    """Initialize session state for authentication"""
    if "user" not in st.session_state:
        st.session_state.user = None
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "auth_error" not in st.session_state:
        st.session_state.auth_error = None
    if "show_password_reset" not in st.session_state:
        st.session_state.show_password_reset = False
    if "reset_email" not in st.session_state:
        st.session_state.reset_email = ""
    if "recovery_token" not in st.session_state:
        st.session_state.recovery_token = None


def get_recovery_token_from_url():
    """Extract recovery token from URL query parameters"""
    try:
        query_params = st.query_params
        token = query_params.get("token")
        token_type = query_params.get("type")
        if token and token_type == "recovery":
            return token
    except:
        pass
    return None


def sign_up(email: str, password: str):
    """Sign up a new user"""
    try:
        response = sb.auth.sign_up({"email": email, "password": password})
        st.session_state.auth_error = None
        return response
    except Exception as e:
        st.session_state.auth_error = str(e)
        return None


def sign_in(email: str, password: str):
    """Sign in an existing user"""
    try:
        response = sb.auth.sign_in_with_password({"email": email, "password": password})
        st.session_state.user = response.user
        st.session_state.access_token = response.session.access_token
        st.session_state.auth_error = None
        return response
    except Exception as e:
        st.session_state.auth_error = str(e)
        return None


def sign_out():
    """Sign out the current user"""
    try:
        sb.auth.sign_out()
        st.session_state.user = None
        st.session_state.access_token = None
        st.session_state.auth_error = None
    except Exception as e:
        st.session_state.auth_error = str(e)


def reset_password(email: str):
    """Send password reset email"""
    try:
        response = sb.auth.reset_password_for_email(
            email,
            {"redirect_to": st.secrets.get("REDIRECT_URL", "http://localhost:8501")}
        )
        st.session_state.auth_error = None
        return True
    except Exception as e:
        st.session_state.auth_error = str(e)
        return False


def update_password(new_password: str):
    """Update password using recovery token"""
    try:
        # The token should be automatically handled by Supabase session
        response = sb.auth.update_user({"password": new_password})
        st.session_state.user = response.user
        st.session_state.auth_error = None
        return True
    except Exception as e:
        st.session_state.auth_error = str(e)
        return False


def get_current_user():
    """Get the currently authenticated user"""
    return st.session_state.get("user")


def is_authenticated():
    """Check if user is currently authenticated"""
    return st.session_state.get("user") is not None


def password_reset_dialog():
    """Render password reset dialog"""
    st.subheader("Reset Password")
    st.write("Enter your email to receive a password reset link.")
    
    reset_email = st.text_input("Email Address", key="reset_email_input")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("Send Reset Link", key="send_reset_button"):
            if reset_email:
                if reset_password(reset_email):
                    st.success("Password reset email sent! Check your inbox.")
                    st.session_state.show_password_reset = False
                    time.sleep(2)
                    st.rerun()
                else:
                    st.error(f"Failed to send reset email: {st.session_state.auth_error}")
            else:
                st.warning("Please enter your email address")
    
    with col2:
        if st.button("Back", key="cancel_reset_button"):
            st.session_state.show_password_reset = False
            st.rerun()

def password_recovery_form():
    st.title("QuantifI - Set New Password")
    st.write("Enter your new password below.")
    
    new_password = st.text_input("New Password", type="password", key="recovery_password")
    confirm_password = st.text_input("Confirm Password", type="password", key="recovery_confirm")
    
    if st.button("Update Password"):
        if new_password == confirm_password:
            if update_password(new_password):
                st.success("Password updated! Redirecting...")
                st.session_state.show_recovery_form = False # Close the form
                time.sleep(2)
                st.rerun()
            else:
                st.error(f"Error: {st.session_state.auth_error}")
        else:
            st.error("Passwords do not match")


def auth_page():
    """Render authentication page with sign in / sign up tabs"""
    
    # 2. HANDLE THE RESET LINK FIRST (The "token_hash" logic)
    query_params = st.query_params
    if "token_hash" in query_params and "type" in query_params:
        token_hash = query_params["token_hash"]
        otp_type = query_params["type"]
        
        try:
            # This 'logs in' the user via the link
            sb.auth.verify_otp({"token_hash": token_hash, "type": otp_type})
            # Clear params so the form stays visible on refresh
            st.query_params.clear()
            st.session_state.show_recovery_form = True 
        except Exception as e:
            st.error(f"Invalid or expired reset link: {e}")

    # 3. Show the Recovery Form if the link was valid
    if st.session_state.get("show_recovery_form"):
        password_recovery_form()
        return

    # 4. Normal Auth Flow logic
    st.title("QuantifI - Authentication")

    if st.session_state.show_password_reset:
        password_reset_dialog()
        return
    tab1, tab2 = st.tabs(["Sign In", "Sign Up"])

    with tab1:
        st.subheader("Sign In")
        with st.form("signin_form"):
            email = st.text_input("Email", key="signin_email")
            password = st.text_input("Password", type="password", key="signin_password")
            signin_submitted = st.form_submit_button("Sign In")

            if signin_submitted:
                if email and password:
                    result = sign_in(email, password)
                    if result:
                        st.success("Signed in successfully!")
                        time.sleep(1)
                        st.rerun()
                    else:
                        st.error(f"Sign in failed: {st.session_state.auth_error}")
                else:
                    st.warning("Please enter email and password")
        
        # Forgot password link
        if st.button("Forgot Password?", key="forgot_password_button"):
            st.session_state.show_password_reset = True
            st.rerun()

    with tab2:
        st.subheader("Create Account")
        with st.form("signup_form"):
            email = st.text_input("Email", key="signup_email")
            password = st.text_input("Password", type="password", key="signup_password")
            password_confirm = st.text_input(
                "Confirm Password", type="password", key="signup_confirm"
            )
            signup_submitted = st.form_submit_button("Sign Up")

            if signup_submitted:
                if not email or not password or not password_confirm:
                    st.warning("Please fill in all fields")
                elif password != password_confirm:
                    st.error("Passwords do not match")
                else:
                    result = sign_up(email, password)
                    if result:
                        st.success("Account created! Please sign in with your credentials.")
                    else:
                        st.error(f"Sign up failed: {st.session_state.auth_error}")
