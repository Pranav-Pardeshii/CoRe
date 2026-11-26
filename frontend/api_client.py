"""Centralized HTTP client for the CoRe FastAPI backend."""

from __future__ import annotations

import json
import os
from dataclasses import dataclass
from typing import Any

import requests
import streamlit as st

DEFAULT_TIMEOUT: tuple[float, float] = (5.0, 15.0)
_SESSION = requests.Session()


def get_api_base_url() -> str:
    """Return the configured backend base URL without a trailing slash."""
    raw = os.getenv("CORE_API_BASE_URL", "http://127.0.0.1:8000").strip()
    return raw.rstrip("/") or "http://127.0.0.1:8000"


@dataclass(frozen=True, slots=True)
class ApiResult:
    """Structured result returned by all backend API calls."""

    ok: bool
    status_code: int
    data: Any = None
    error: str | None = None


def _extract_error_detail(payload: Any, status_code: int) -> str:
    if isinstance(payload, dict):
        detail = payload.get("detail")
        if isinstance(detail, str) and detail.strip():
            return detail
        if isinstance(detail, list) and detail:
            messages = [
                str(item.get("msg", item)) if isinstance(item, dict) else str(item)
                for item in detail
            ]
            return "; ".join(messages)
    return f"Request failed with status {status_code}."


def _parse_json_safely(response: requests.Response) -> tuple[bool, Any]:
    content_type = response.headers.get("Content-Type", "").lower()
    if "application/json" not in content_type and not response.text.lstrip().startswith(("{", "[")):
        return False, None
    try:
        return True, response.json()
    except (ValueError, json.JSONDecodeError):
        return False, None


def _handle_unauthorized() -> None:
    st.session_state["token"] = None
    st.session_state["username"] = None
    st.session_state.pop("saved_list_cache", None)
    st.session_state["session_expired_notice"] = "Your session has expired. Please log in again."
    st.rerun()


def request_api(
    method: str,
    path: str,
    *,
    params: dict[str, Any] | None = None,
    json_body: dict[str, Any] | None = None,
    form_data: dict[str, Any] | None = None,
    token: str | None = None,
    require_auth: bool = False,
) -> ApiResult:
    """Execute an HTTP request against the backend with timeouts and safe error handling."""
    url = f"{get_api_base_url()}{path}"
    headers: dict[str, str] = {}
    if token:
        headers["Authorization"] = f"Bearer {token}"

    try:
        response = _SESSION.request(
            method=method,
            url=url,
            params=params,
            json=json_body,
            data=form_data,
            headers=headers or None,
            timeout=DEFAULT_TIMEOUT,
        )
    except requests.RequestException as exc:
        return ApiResult(
            ok=False,
            status_code=0,
            error=f"Could not reach the server: {exc}",
        )

    if response.status_code == 401 and (require_auth or token is not None):
        _handle_unauthorized()
        return ApiResult(ok=False, status_code=401, error="Session expired.")

    parsed_ok, payload = _parse_json_safely(response)
    if response.status_code != 200:
        if parsed_ok:
            return ApiResult(
                ok=False,
                status_code=response.status_code,
                data=payload,
                error=_extract_error_detail(payload, response.status_code),
            )
        return ApiResult(
            ok=False,
            status_code=response.status_code,
            error=f"Server returned an unexpected response (HTTP {response.status_code}).",
        )

    if not parsed_ok:
        return ApiResult(
            ok=False,
            status_code=response.status_code,
            error="Server returned a non-JSON response.",
        )

    return ApiResult(ok=True, status_code=response.status_code, data=payload)


def login_user(username: str, password: str) -> ApiResult:
    """Authenticate a user via POST /auth/login (OAuth2 form-encoded)."""
    return request_api(
        "POST",
        "/auth/login",
        form_data={"username": username, "password": password},
    )


def register_user(username: str, password: str) -> ApiResult:
    """Register a new user via POST /auth/register."""
    return request_api(
        "POST",
        "/auth/register",
        json_body={"username": username, "password": password},
    )


def fetch_catalog_filters() -> ApiResult:
    """Fetch distinct filter values from GET /catalog/filters."""
    return request_api("GET", "/catalog/filters")


def fetch_recommendations(params: dict[str, Any]) -> ApiResult:
    """Fetch paginated college recommendations from GET /recommender/."""
    return request_api("GET", "/recommender/", params=params)


def fetch_trends(branch_code: str, category: str) -> ApiResult:
    """Fetch historical cutoff trends from GET /trends/."""
    return request_api(
        "GET",
        "/trends/",
        params={"branch_code": branch_code, "category": category},
    )


def get_saved_list(token: str) -> ApiResult:
    """Fetch the authenticated user's saved list via GET /saved-lists/."""
    return request_api("GET", "/saved-lists/", token=token, require_auth=True)


def add_saved_list_item(token: str, branch_code: str) -> ApiResult:
    """Save a branch to the authenticated user's list via POST /saved-lists/."""
    return request_api(
        "POST",
        "/saved-lists/",
        json_body={"branch_code": branch_code},
        token=token,
        require_auth=True,
    )


def delete_saved_list_item(token: str, item_id: int) -> ApiResult:
    """Remove a saved item via DELETE /saved-lists/{item_id}."""
    return request_api(
        "DELETE",
        f"/saved-lists/{item_id}",
        token=token,
        require_auth=True,
    )


def reorder_saved_list(token: str, ordered_ids: list[int]) -> ApiResult:
    """Reorder saved list items via PUT /saved-lists/."""
    return request_api(
        "PUT",
        "/saved-lists/",
        json_body={"ordered_list": ordered_ids},
        token=token,
        require_auth=True,
    )
