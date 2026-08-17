import streamlit as st
import requests

API_URL_AUTH = "https://core-5y5r.onrender.com/auth"


def is_logged_in() -> bool:
    return bool(st.session_state.get("token"))


def get_token() -> str | None:
    """For saved_list requests: Authorization: Bearer {get_token()}"""
    return st.session_state.get("token")


def get_username() -> str | None:
    return st.session_state.get("username")


def _do_login(username: str, password: str):
    # /auth/login expects OAuth2PasswordRequestForm -> form-encoded, not JSON
    response = requests.post(
        f"{API_URL_AUTH}/login",
        data={"username": username, "password": password},
        timeout=15,
    )
    data = response.json()
    if response.status_code != 200:
        st.error(data.get("detail", "Login failed."))
        return

    st.session_state["token"] = data["access_token"]
    st.session_state["username"] = username
    st.rerun()


def _do_register(username: str, password: str):
    # /auth/register expects a plain JSON body (UserSchema)
    response = requests.post(
        f"{API_URL_AUTH}/register",
        json={"username": username, "password": password},
        timeout=15,
    )
    data = response.json()
    if response.status_code != 200:
        st.error(data.get("detail", "Registration failed."))
        return

    st.success("Account created. Log in below.")
    st.session_state["auth_mode"] = "login"
    st.rerun()


def _do_logout():
    st.session_state["token"] = None
    st.session_state["username"] = None
    st.rerun()


def render_auth_sidebar():
    """Call this once near the top of the app. Renders login/register/logout
    in the sidebar. Session-only: token is lost on a hard refresh (accepted
    trade-off for v1 — no browser-storage dependency to fight with)."""
    with st.sidebar:
        if is_logged_in():
            st.markdown(f"Logged in as **{get_username()}**")
            if st.button("Log out", use_container_width=True):
                _do_logout()
        else:
            st.markdown("### Account")
            if "auth_mode" not in st.session_state:
                st.session_state["auth_mode"] = "login"

            mode_col1, mode_col2 = st.columns(2)
            with mode_col1:
                if st.button("Login", use_container_width=True,
                              type="primary" if st.session_state["auth_mode"] == "login" else "secondary"):
                    st.session_state["auth_mode"] = "login"
            with mode_col2:
                if st.button("Register", use_container_width=True,
                              type="primary" if st.session_state["auth_mode"] == "register" else "secondary"):
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
                if st.button("Create account", use_container_width=True):
                    if not username or not password:
                        st.warning("Enter both username and password.")
                    else:
                        _do_register(username, password)