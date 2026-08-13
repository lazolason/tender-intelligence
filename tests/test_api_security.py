import sys
from types import ModuleType

import pytest

pytest.importorskip("flask")

import app as app_module


@pytest.fixture(autouse=True)
def reset_security_state(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", "")
    with app_module.RATE_LIMIT_LOCK:
        app_module.RATE_LIMIT_STATE.clear()


def test_protected_endpoint_fails_closed_without_api_key():
    response = app_module.app.test_client().post(
        "/api/bids",
        json={"ref": "SEC-1", "outcome": "won", "submitted": True},
    )

    assert response.status_code == 503
    assert response.get_json()["error"] == "Protected API is not configured"


def test_protected_endpoint_rejects_wrong_key(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", "correct-secret")
    response = app_module.app.test_client().post(
        "/api/bids",
        headers={"X-API-Key": "wrong-secret"},
        json={"ref": "SEC-1", "outcome": "won", "submitted": True},
    )

    assert response.status_code == 401
    assert response.get_json() == {"error": "Unauthorized"}


def test_authenticated_daily_trigger_is_post_only(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", "correct-secret")
    daily_module = ModuleType("daily_runner")
    daily_module.run_daily = lambda: {"scan": {"status": "success"}}
    monkeypatch.setitem(sys.modules, "daily_runner", daily_module)
    client = app_module.app.test_client()

    assert client.get("/api/run/daily").status_code == 405
    response = client.post(
        "/api/run/daily",
        headers={"Authorization": "Bearer correct-secret"},
    )

    assert response.status_code == 200
    assert response.get_json()["status"] == "success"


def test_untrusted_forwarded_for_does_not_change_rate_limit_identity(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", "correct-secret")
    daily_module = ModuleType("daily_runner")
    daily_module.run_daily = lambda: {"scan": {"status": "success"}}
    monkeypatch.setitem(sys.modules, "daily_runner", daily_module)
    client = app_module.app.test_client()

    statuses = []
    for index in range(4):
        response = client.post(
            "/api/run/daily",
            headers={
                "Authorization": "Bearer correct-secret",
                "X-Forwarded-For": f"203.0.113.{index}",
            },
        )
        statuses.append(response.status_code)

    assert statuses == [200, 200, 200, 429]


def test_security_headers_and_cors_default():
    response = app_module.app.test_client().get(
        "/",
        headers={"Origin": "https://attacker.example"},
    )

    assert response.status_code == 200
    assert response.headers["X-Content-Type-Options"] == "nosniff"
    assert response.headers["X-Frame-Options"] == "DENY"
    assert response.headers["Referrer-Policy"] == "no-referrer"
    assert "frame-ancestors 'none'" in response.headers["Content-Security-Policy"]
    assert response.headers.get("Access-Control-Allow-Origin") is None


def test_request_body_limit_is_enforced(monkeypatch):
    monkeypatch.setattr(app_module, "API_KEY", "correct-secret")
    response = app_module.app.test_client().post(
        "/api/bids",
        headers={
            "Authorization": "Bearer correct-secret",
            "Content-Type": "application/json",
        },
        data='{"note":"' + ("x" * 70000) + '"}',
    )

    assert response.status_code == 413
