"""Authentication sidebar UI for CoRe."""

from __future__ import annotations

import streamlit as st

from frontend.api_client import login_user, register_user


def is_logged_in() -> bool:
    """Return True if a bearer token is present in session state."""
    return bool(st.session_state.get("token"))


def get_token() -> str | None:
    """Return the active bearer token for authenticated requests."""
    token = st.session_state.get("token")
    return str(token) if token else None


def get_username() -> str | None:
    """Return the logged-in user's username."""
    username = st.session_state.get("username")
    return str(username) if username else None


def _clear_user_session() -> None:
    st.session_state["token"] = None
    st.session_state["username"] = None
    st.session_state.pop("saved_list_cache", None)


def _do_login(username: str, password: str) -> None:
    result = login_user(username.strip(), password)
    if not result.ok:
        st.error(result.error or "Login failed.")
        return

    _clear_user_session()
    st.session_state.pop("session_expired_notice", None)
    st.session_state["token"] = result.data["access_token"]
    st.session_state["username"] = username.strip()
    st.rerun()


def _do_register(username: str, password: str) -> None:
    cleaned_username = username.strip()
    if len(cleaned_username) < 3 or len(cleaned_username) > 50:
        st.warning("Username must be between 3 and 50 characters.")
        return
    if len(password) < 8 or len(password) > 128:
        st.warning("Password must be between 8 and 128 characters.")
        return

    result = register_user(cleaned_username, password)
    if not result.ok:
        st.error(result.error or "Registration failed.")
        return

    st.success("Account created. Log in below.")
    st.session_state["auth_mode"] = "login"
    st.rerun()


def _do_logout() -> None:
    _clear_user_session()
    st.rerun()


def render_auth_sidebar() -> None:
    """Render login/register/logout controls in the Streamlit sidebar."""
    with st.sidebar:
        expired_notice = st.session_state.pop("session_expired_notice", None)
        if expired_notice:
            st.warning(expired_notice)

        if is_logged_in():
            st.markdown(f"Logged in as **{get_username()}**")
            if st.button("Log out", use_container_width=True):
                _do_logout()
            return

        st.markdown("### Account")
        if "auth_mode" not in st.session_state:
            st.session_state["auth_mode"] = "login"

        mode_col1, mode_col2 = st.columns(2)
        with mode_col1:
            if st.button(
                "Login",
                use_container_width=True,
                type="primary" if st.session_state["auth_mode"] == "login" else "secondary",
            ):
                st.session_state["auth_mode"] = "login"
        with mode_col2:
            if st.button(
                "Register",
                use_container_width=True,
                type="primary" if st.session_state["auth_mode"] == "register" else "secondary",
            ):
                st.session_state["auth_mode"] = "register"

        username = st.text_input("Username", key="auth_username")
        password = st.text_input("Password", type="password", key="auth_password")

        if st.session_state["auth_mode"] == "login":
            if st.button("Log in", use_container_width=True):
                if not username or not password:
                    st.warning("Enter both username and password.")
                else:
                    _do_login(username, password)
        else:
            st.caption(
                "Username: 3-50 chars (letters, digits, '.', '_', '-'). Password: 8-128 chars."
            )
            if st.button("Create account", use_container_width=True):
                if not username or not password:
                    st.warning("Enter both username and password.")
                else:
                    _do_register(username, password)
