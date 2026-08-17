import streamlit as st
import requests
from auth_ui import get_token, is_logged_in

API_URL_SAVED_LIST = "https://core-5y5r.onrender.com/saved-lists/"


def _auth_headers():
    return {"Authorization": f"Bearer {get_token()}"}


def save_college(branch_code: str):
    """POST /saved-lists/ — save a single branch_code for the logged-in user."""
    response = requests.post(
        API_URL_SAVED_LIST,
        json={"branch_code": branch_code},
        headers=_auth_headers(),
        timeout=15,
    )
    data = response.json()
    if response.status_code != 200:
        st.toast(data.get("detail", "Couldn't save."), icon="⚠️")
    else:
        st.toast("Saved to your list.", icon="✅")
        # force the sidebar list to refetch next render
        st.session_state.pop("saved_list_cache", None)


def _fetch_saved_list():
    response = requests.get(API_URL_SAVED_LIST, headers=_auth_headers(), timeout=15)
    data = response.json()
    if response.status_code != 200:
        st.error(data.get("detail", "Couldn't load saved list."))
        return []
    return data["saved_list"]


def _delete_item(item_id: int):
    response = requests.delete(f"{API_URL_SAVED_LIST}{item_id}", headers=_auth_headers(), timeout=15)
    data = response.json()
    if response.status_code != 200:
        st.error(data.get("detail", "Couldn't delete item."))
        return
    st.session_state.pop("saved_list_cache", None)
    st.rerun()


def _reorder(ordered_ids: list[int]):
    response = requests.put(
        API_URL_SAVED_LIST,
        json={"ordered_list": ordered_ids},
        headers=_auth_headers(),
        timeout=15,
    )
    data = response.json()
    if response.status_code != 200:
        st.error(data.get("detail", "Couldn't reorder."))
        return
    st.session_state.pop("saved_list_cache", None)
    st.rerun()


def render_saved_list_sidebar():
    """Call after render_auth_sidebar(). Only shows anything if logged in."""
    if not is_logged_in():
        return

    with st.sidebar:
        st.markdown("---")
        st.markdown("### My Saved List")

        if "saved_list_cache" not in st.session_state:
            st.session_state["saved_list_cache"] = _fetch_saved_list()

        items = st.session_state["saved_list_cache"]

        if not items:
            st.caption("Nothing saved yet.")
            return

        ids_in_order = [item["id"] for item in items]

        for idx, item in enumerate(items):
            col_text, col_up, col_down, col_del = st.columns([5, 1, 1, 1])
            with col_text:
                st.markdown(f"**{item['college_name']}**  \n{item['branch_name']}")
            with col_up:
                if idx > 0 and st.button("↑", key=f"up_{item['id']}"):
                    new_order = ids_in_order.copy()
                    new_order[idx - 1], new_order[idx] = new_order[idx], new_order[idx - 1]
                    _reorder(new_order)
            with col_down:
                if idx < len(items) - 1 and st.button("↓", key=f"down_{item['id']}"):
                    new_order = ids_in_order.copy()
                    new_order[idx + 1], new_order[idx] = new_order[idx], new_order[idx + 1]
                    _reorder(new_order)
            with col_del:
                if st.button("✕", key=f"del_{item['id']}"):
                    _delete_item(item["id"])