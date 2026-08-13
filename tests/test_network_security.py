from types import SimpleNamespace

import pytest

from utils.retry_tools import (
    _requests_get_with_retry,
    secure_request_kwargs,
    validate_outbound_url,
)


def test_outbound_url_policy_requires_https_and_rejects_private_targets():
    assert validate_outbound_url("https://www.etenders.gov.za/tenders")

    for url in (
        "http://example.com/tenders",
        "https://localhost/admin",
        "https://127.0.0.1/admin",
        "https://10.0.0.1/admin",
        "file:///etc/passwd",
        "javascript:alert(1)",
    ):
        with pytest.raises(ValueError):
            validate_outbound_url(url)


def test_loopback_http_requires_explicit_development_exception():
    assert (
        validate_outbound_url(
            "http://127.0.0.1:5001/health",
            allow_local_http=True,
        )
        == "http://127.0.0.1:5001/health"
    )


def test_secure_request_kwargs_enforces_verification_and_timeout():
    assert secure_request_kwargs({}) == {"verify": True, "timeout": 30}
    assert secure_request_kwargs({"verify": True, "timeout": 5}) == {
        "verify": True,
        "timeout": 5,
    }
    with pytest.raises(ValueError, match="cannot be disabled"):
        secure_request_kwargs({"verify": False})


def test_safe_request_rejects_https_to_http_redirect(monkeypatch):
    response = SimpleNamespace(
        status_code=200,
        url="http://example.com/downgraded",
        close=lambda: None,
    )
    captured = {}

    def fake_get(url, **kwargs):
        captured.update(kwargs)
        return response

    monkeypatch.setattr("utils.retry_tools.requests.get", fake_get)

    with pytest.raises(ValueError, match="insecure"):
        _requests_get_with_retry("https://example.com/start")
    assert captured["verify"] is True
    assert captured["timeout"] == 30
