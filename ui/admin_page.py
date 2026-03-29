import streamlit as st
import auth
from auth_engine import AuthEngine


def render_admin_page():
    st.header("Admin")

    if not auth.is_admin():
        st.error("Not authorized.")
        st.caption("Set `ADMIN_EMAILS` in Streamlit secrets to enable this page for specific users.")
        return

    st.markdown(
        """
This sends a **Supabase Auth invite email** (app account).

If your deployed app is set to **Private** on Streamlit Community Cloud, users may still be asked to log in to Streamlit
*before* they can reach your app. For end-user access controlled by Supabase, set the Streamlit app visibility to
**Public/Unlisted** and manage access here (or in Supabase Auth settings).
""".strip()
    )

    with st.form("invite_user_form", border=True):
        email = st.text_input("Invitee email", placeholder="name@example.com")
        submitted = st.form_submit_button("Send Invite", type="primary", use_container_width=True)

    if submitted:
        email_clean = (email or "").strip().lower()
        ok, err = AuthEngine.invite_user(email_clean)
        if ok:
            st.success("Invite sent (if the email is valid).")
            st.session_state.pop("invite_already_registered_email", None)
        else:
            st.error(err or "Invite failed.")
            if err and "already been registered" in err.lower():
                st.session_state["invite_already_registered_email"] = email_clean
    st.caption("Note: Invites only work for new emails. Use password reset for existing users.")

    registered_email = st.session_state.get("invite_already_registered_email")
    if registered_email:
        st.warning("This email is already registered. Send a password reset instead?")
        if st.button("Send Password Reset Instead", type="secondary", use_container_width=True):
            ok, err = AuthEngine.request_reset(registered_email)
            if ok:
                st.success("Password reset sent (if the email is valid).")
                st.session_state.pop("invite_already_registered_email", None)
            else:
                st.error(err or "Password reset failed.")

    with st.form("resend_invite_form", border=True):
        resend_email = st.text_input("Resend invite email", placeholder="name@example.com")
        resend_submitted = st.form_submit_button("Resend Invite", type="secondary", use_container_width=True)

    if resend_submitted:
        ok, err = AuthEngine.invite_user(resend_email)
        if ok:
            st.success("Invite re-sent (if the email is valid and not yet registered).")
        else:
            st.error(err or "Resend failed.")

    with st.form("reset_user_form", border=True):
        reset_email = st.text_input("Password reset email", placeholder="name@example.com")
        reset_submitted = st.form_submit_button("Send Password Reset", type="secondary", use_container_width=True)

    if reset_submitted:
        ok, err = AuthEngine.request_reset(reset_email)
        if ok:
            st.success("Password reset sent (if the email is valid).")
        else:
            st.error(err or "Password reset failed.")
    st.caption("Use password reset for existing users who need to set or change their password.")
