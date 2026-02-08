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
        ok, err = AuthEngine.invite_user(email)
        if ok:
            st.success("Invite sent (if the email is valid).")
        else:
            st.error(err or "Invite failed.")

