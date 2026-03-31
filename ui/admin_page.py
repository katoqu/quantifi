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
Approve users to sign up **without sending email** by adding their email to the allowlist.

If your deployed app is set to **Private** on Streamlit Community Cloud, users may still be asked to log in to Streamlit
*before* they can reach your app. For end-user access controlled by Supabase, set the Streamlit app visibility to
**Public/Unlisted** and manage access here (or in Supabase Auth settings).
""".strip()
    )

    with st.form("allowlist_user_form", border=True):
        allow_email = st.text_input("Allowlist email", placeholder="name@example.com")
        allow_submitted = st.form_submit_button("Approve Signup", type="primary", use_container_width=True)

    if allow_submitted:
        ok, err = AuthEngine.add_allowlist_email(allow_email)
        if ok:
            st.success("Email approved for signup.")
        else:
            st.error(err or "Allowlist update failed.")

    st.caption("Approved users can open the Sign Up screen, set a password, and create their account.")
