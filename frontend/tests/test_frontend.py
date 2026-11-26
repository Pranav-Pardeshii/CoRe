"""Unit tests for frontend.category_labels and frontend.api_client."""

from __future__ import annotations

from typing import Any
from unittest.mock import MagicMock

import pytest
import requests
from frontend import api_client
from frontend.category_labels import decode_category


@pytest.mark.parametrize(
    ("code", "expected"),
    [
        ("All", "All — All Categories"),
        ("ALL", "All — All Categories"),
        ("GOPENS", "GOPENS — General, Open, State Level"),
        ("LSEBCH", "LSEBCH — Ladies-only, SEBC, Home University"),
        ("DEFRNT1O", "DEFRNT1O — Defence (Common Reserved), NT1, Other than Home University"),
        ("TFWS", "TFWS — Tuition Fee Waiver Scheme"),
        ("EWS", "EWS — Economically Weaker Section"),
        ("ORPHAN", "ORPHAN — Orphan"),
        ("MI", "MI — Minority"),
        ("UNKNOWN_CODE", "UNKNOWN_CODE"),
    ],
)
def test_decode_category(code: str, expected: str) -> None:
    """decode_category handles All/ALL, standard codes, standalone codes, and unparsed fallback."""
    assert decode_category(code) == expected


def _mock_response(
    status_code: int,
    *,
    json_data: Any = None,
    text: str = "",
    content_type: str = "application/json",
) -> MagicMock:
    resp = MagicMock(spec=requests.Response)
    resp.status_code = status_code
    resp.headers = {"Content-Type": content_type}
    resp.text = text
    if json_data is not None:
        resp.json.return_value = json_data
    else:
        resp.json.side_effect = ValueError("No JSON")
    return resp


def test_api_base_url_strips_trailing_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    """get_api_base_url reads CORE_API_BASE_URL and strips trailing slash."""
    monkeypatch.setenv("CORE_API_BASE_URL", "https://api.example.com/")
    assert api_client.get_api_base_url() == "https://api.example.com"


def test_api_client_handles_request_exception(monkeypatch: pytest.MonkeyPatch) -> None:
    """Network errors return a clean ApiResult without raising."""

    def raise_conn_error(*_args: Any, **_kwargs: Any) -> None:
        raise requests.ConnectionError("connection refused")

    monkeypatch.setattr(api_client._SESSION, "request", raise_conn_error)
    res = api_client.fetch_catalog_filters()
    assert not res.ok
    assert res.status_code == 0
    assert res.error is not None and "Could not reach the server" in res.error


def test_api_client_handles_non_json_502_gracefully(monkeypatch: pytest.MonkeyPatch) -> None:
    """Non-JSON 502/503/500 responses never raise JSONDecodeError."""
    bad_gateway = _mock_response(
        502,
        text="<html><body>502 Bad Gateway</body></html>",
        content_type="text/html",
    )
    monkeypatch.setattr(api_client._SESSION, "request", lambda **_kw: bad_gateway)

    res = api_client.fetch_recommendations({"percentile": 90})
    assert not res.ok
    assert res.status_code == 502
    assert res.error == "Server returned an unexpected response (HTTP 502)."


def test_api_client_extracts_422_and_409_details(monkeypatch: pytest.MonkeyPatch) -> None:
    """422 list details and 409 string details are surfaced cleanly."""
    resp_422 = _mock_response(
        422,
        json_data={"detail": [{"msg": "String should have at least 8 characters"}]},
    )
    monkeypatch.setattr(api_client._SESSION, "request", lambda **_kw: resp_422)
    res = api_client.register_user("alice", "short")
    assert not res.ok
    assert res.status_code == 422
    assert "at least 8 characters" in (res.error or "")

    resp_409 = _mock_response(409, json_data={"detail": "Username already exists."})
    monkeypatch.setattr(api_client._SESSION, "request", lambda **_kw: resp_409)
    res_dup = api_client.register_user("alice", "password123")
    assert not res_dup.ok
    assert res_dup.status_code == 409
    assert res_dup.error == "Username already exists."


def test_api_client_401_clears_session_and_reruns(monkeypatch: pytest.MonkeyPatch) -> None:
    """401 on an authenticated call wipes token/username/saved_list_cache and triggers rerun."""
    fake_state: dict[str, Any] = {
        "token": "stale-jwt",
        "username": "alice",
        "saved_list_cache": [{"id": 1}],
    }
    rerun_called = {"count": 0}

    monkeypatch.setattr(api_client.st, "session_state", fake_state)
    monkeypatch.setattr(
        api_client.st,
        "rerun",
        lambda: rerun_called.__setitem__("count", rerun_called["count"] + 1),
    )

    resp_401 = _mock_response(401, json_data={"detail": "Invalid or expired token"})
    monkeypatch.setattr(api_client._SESSION, "request", lambda **_kw: resp_401)

    res = api_client.get_saved_list("stale-jwt")
    assert not res.ok
    assert res.status_code == 401
    assert fake_state["token"] is None
    assert fake_state["username"] is None
    assert "saved_list_cache" not in fake_state
    assert "expired" in fake_state["session_expired_notice"].lower()
    assert rerun_called["count"] == 1


def test_api_client_uses_exact_routes_and_timeouts(monkeypatch: pytest.MonkeyPatch) -> None:
    """Requests use exact trailing slashes and explicit (5.0, 15.0) timeouts."""
    captured: list[dict[str, Any]] = []

    def fake_request(**kwargs: Any) -> MagicMock:
        captured.append(kwargs)
        return _mock_response(200, json_data={"ok": True})

    monkeypatch.setenv("CORE_API_BASE_URL", "http://127.0.0.1:8000")
    monkeypatch.setattr(api_client._SESSION, "request", fake_request)

    api_client.fetch_catalog_filters()
    api_client.fetch_recommendations({"percentile": 95})
    api_client.fetch_trends("0627124510", "GOPENS")
    api_client.get_saved_list("tok")

    assert [c["url"] for c in captured] == [
        "http://127.0.0.1:8000/catalog/filters",
        "http://127.0.0.1:8000/recommender/",
        "http://127.0.0.1:8000/trends/",
        "http://127.0.0.1:8000/saved-lists/",
    ]
    assert all(c["timeout"] == (5.0, 15.0) for c in captured)
