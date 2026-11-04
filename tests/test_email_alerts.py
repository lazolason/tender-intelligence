"""Offline verification of the email digest wiring.

The path was previously "configured" only in name: daily_runner compared the
sender against a literal placeholder, so behaviour was never exercised.
"""
import json
import ssl
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import utils.email_alerts as ea


class FakeSMTP:
    """Records send_email()'s calls instead of opening a socket."""

    instances = []

    def __init__(self, host, port, timeout=None):
        self.host, self.port = host, port
        self.timeout = timeout
        self.started_tls = False
        self.credentials = None
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self, context=None):
        self.started_tls = True
        self.tls_context = context

    def login(self, user, password):
        self.credentials = (user, password)

    def sendmail(self, sender, recipients, message):
        self.sent = (sender, recipients, message)


@pytest.fixture
def fake_smtp(monkeypatch):
    FakeSMTP.instances.clear()
    monkeypatch.setattr(ea.smtplib, "SMTP", FakeSMTP)
    return FakeSMTP


def _config(**overrides):
    cfg = {
        "smtp_server": "smtp.gmail.com",
        "smtp_port": 587,
        "sender_email": "tenders@mexel.co.za",
        "sender_password": "app-password",
        "recipient_emails": ["ops@mexel.co.za"],
    }
    cfg.update(overrides)
    return cfg


def test_config_status_lists_each_missing_field():
    status = ea.config_status(_config(sender_email="", sender_password="", recipient_emails=[]))
    assert status["configured"] is False
    assert len(status["missing"]) == 3


def test_config_status_complete():
    status = ea.config_status(_config())
    assert status["configured"] is True
    assert status["missing"] == []


def test_send_email_refuses_when_unconfigured(fake_smtp, monkeypatch):
    monkeypatch.setattr(ea, "EMAIL_CONFIG", _config(sender_email="", recipient_emails=[]))
    assert ea.send_email("subject", "<p>body</p>") is False
    assert fake_smtp.instances == []


def test_send_email_starts_tls_authenticates_and_sends(fake_smtp, monkeypatch):
    monkeypatch.setattr(ea, "EMAIL_CONFIG", _config())

    assert ea.send_email("Test digest", "<p>hello</p>") is True

    server = fake_smtp.instances[0]
    assert (server.host, server.port) == ("smtp.gmail.com", 587)
    assert server.started_tls is True
    assert server.timeout == 30
    assert server.tls_context.verify_mode == ssl.CERT_REQUIRED
    assert server.tls_context.check_hostname is True
    assert server.credentials == ("tenders@mexel.co.za", "app-password")
    sender, recipients, message = server.sent
    assert sender == "tenders@mexel.co.za"
    assert recipients == ["ops@mexel.co.za"]
    assert "Subject: Test digest" in message


def test_mailctl_credentials_are_used_as_fallback(tmp_path, monkeypatch):
    """One shared app password should serve both mailctl and the digest."""
    creds = tmp_path / "credentials.json"
    creds.write_text(json.dumps({"owner@piso.co.za": "abcd efgh ijkl mnop"}))

    monkeypatch.setattr(ea, "_MAILCTL_CREDENTIAL_PATHS", [creds])
    for var in (
        "SMTP_USER", "TENDERSCAN_SMTP_USER",
        "SMTP_PASSWORD", "TENDERSCAN_SMTP_PASSWORD",
        "EMAIL_FROM", "TENDERSCAN_EMAIL_FROM",
        "EMAIL_TO", "TENDERSCAN_EMAIL_TO",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = ea.load_email_config()
    assert cfg["sender_email"] == "owner@piso.co.za"
    assert cfg["sender_password"] == "abcd efgh ijkl mnop"
    # Digest defaults to the sending account rather than being dropped.
    assert cfg["recipient_emails"] == ["owner@piso.co.za"]


def test_placeholder_values_are_not_treated_as_configured():
    """A copied .env must not look configured.

    .env ships TENDERSCAN_SMTP_USER=your-email@gmail.com and example recipients;
    treating those as real made the daily run attempt an SMTP login.
    """
    status = ea.config_status(_config(
        sender_email="your-email@gmail.com",
        sender_password="your-app-password",
        recipient_emails=["recipient1@example.com", "recipient2@example.com"],
    ))

    assert status["configured"] is False
    assert len(status["missing"]) == 3
    assert status["sender"] is None
    assert status["recipients"] == []


def test_send_email_refuses_placeholder_credentials(fake_smtp, monkeypatch):
    monkeypatch.setattr(ea, "EMAIL_CONFIG", _config(
        sender_email="your-email@gmail.com",
        sender_password="your-app-password",
    ))

    assert ea.send_email("digest", "<p>body</p>") is False
    assert fake_smtp.instances == []


def test_real_values_remain_configured():
    status = ea.config_status(_config())
    assert status["configured"] is True
    assert status["sender"] == "tenders@mexel.co.za"
    assert status["recipients"] == ["ops@mexel.co.za"]
