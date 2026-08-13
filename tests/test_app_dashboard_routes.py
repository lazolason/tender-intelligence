import json

import pytest

pytest.importorskip("flask")

import app as app_module
from app import app


def test_flask_serves_dashboard_shell():
    client = app.test_client()
    response = client.get("/")

    assert response.status_code == 200
    assert b"Tender Intelligence Dashboard" in response.data


def test_flask_serves_dashboard_payload_and_assets():
    client = app.test_client()

    tenders_response = client.get("/tenders.json")
    assert tenders_response.status_code == 200
    payload = json.loads(tenders_response.data)
    assert isinstance(payload.get("tenders"), list)

    js_response = client.get("/js/bridge.js")
    assert js_response.status_code == 200
    assert b"resolveApiBaseUrl" in js_response.data

    icon_response = client.get("/icons/icon-192x192.png")
    assert icon_response.status_code == 200


def test_flask_returns_404_for_unknown_api_like_dashboard_path():
    client = app.test_client()
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404


def test_expected_dashboard_count_matches_profile_filter(tmp_path, monkeypatch):
    import sqlite3

    db_path = tmp_path / "tenders.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute("CREATE TABLE tenders (status TEXT, category TEXT)")
        conn.executemany(
            "INSERT INTO tenders VALUES (?, ?)",
            [
                ("Open", "MEXEL"),
                ("Active", "PHAKATHI"),
                ("Open", "EXCLUDED"),
                ("Closed", "MEXEL"),
            ],
        )

        monkeypatch.setattr(app_module, "DASHBOARD_SHOW_ALL", False)
        monkeypatch.setitem(app_module.APP_CONFIG, "classification", {"mexel_only": False})
        assert app_module._expected_dashboard_record_count(conn) == 2

        monkeypatch.setitem(app_module.APP_CONFIG, "classification", {"mexel_only": True})
        assert app_module._expected_dashboard_record_count(conn) == 1

        monkeypatch.setattr(app_module, "DASHBOARD_SHOW_ALL", True)
        assert app_module._expected_dashboard_record_count(conn) == 3
