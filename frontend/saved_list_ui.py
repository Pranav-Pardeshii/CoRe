"""Saved list sidebar UI for CoRe."""

from __future__ import annotations

from typing import Any

import streamlit as st

from frontend.api_client import (
    add_saved_list_item,
    delete_saved_list_item,
    get_saved_list,
    reorder_saved_list,
)
from frontend.auth_ui import get_token, is_logged_in


def save_college(branch_code: str) -> None:
    """Save a branch_code to the logged-in user's preference list."""
    token = get_token()
    if not token:
        st.toast("Please log in to save colleges.", icon="⚠️")
        return

    result = add_saved_list_item(token, branch_code)
    if not result.ok:
        st.toast(result.error or "Couldn't save.", icon="⚠️")
        return

    st.toast("Saved to your list.", icon="✅")
    st.session_state.pop("saved_list_cache", None)
    st.rerun()


def _fetch_saved_list() -> list[dict[str, Any]]:
    token = get_token()
    if not token:
        return []

    result = get_saved_list(token)
    if not result.ok:
        st.error(result.error or "Couldn't load saved list.")
        return []
    return list(result.data.get("saved_list", []))


def _delete_item(item_id: int) -> None:
    token = get_token()
    if not token:
        return

    result = delete_saved_list_item(token, item_id)
    if not result.ok:
        st.error(result.error or "Couldn't delete item.")
        return
    st.session_state.pop("saved_list_cache", None)
    st.rerun()


def _reorder(ordered_ids: list[int]) -> None:
    token = get_token()
    if not token:
        return

    result = reorder_saved_list(token, ordered_ids)
    if not result.ok:
        st.error(result.error or "Couldn't reorder.")
        return
    st.session_state.pop("saved_list_cache", None)
    st.rerun()


def render_saved_list_sidebar() -> None:
    """Render the logged-in user's saved list in the sidebar."""
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

        ids_in_order = [int(item["id"]) for item in items]

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
                    _delete_item(int(item["id"]))
