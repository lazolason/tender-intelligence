"""Offline verification of the email digest wiring.

The path was previously "configured" only in name: daily_runner compared the
sender against a literal placeholder, so behaviour was never exercised.
"""
import json
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import utils.email_alerts as ea


class FakeSMTP:
    """Records send_email()'s calls instead of opening a socket."""

    instances = []

    def __init__(self, host, port):
        self.host, self.port = host, port
        self.started_tls = False
        self.credentials = None
        self.sent = None
        FakeSMTP.instances.append(self)

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False

    def starttls(self):
        self.started_tls = True

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
        "sender_email": "tenders@example.com",
        "sender_password": "app-password",
        "recipient_emails": ["ops@example.com"],
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
    assert server.credentials == ("tenders@example.com", "app-password")
    sender, recipients, message = server.sent
    assert sender == "tenders@example.com"
    assert recipients == ["ops@example.com"]
    assert "Subject: Test digest" in message


def test_mailctl_credentials_are_used_as_fallback(tmp_path, monkeypatch):
    """One shared app password should serve both mailctl and the digest."""
    creds = tmp_path / "credentials.json"
    creds.write_text(json.dumps({"owner@example.com": "abcd efgh ijkl mnop"}))

    monkeypatch.setattr(ea, "_MAILCTL_CREDENTIAL_PATHS", [creds])
    for var in (
        "SMTP_USER", "TENDERSCAN_SMTP_USER",
        "SMTP_PASSWORD", "TENDERSCAN_SMTP_PASSWORD",
        "EMAIL_FROM", "TENDERSCAN_EMAIL_FROM",
        "EMAIL_TO", "TENDERSCAN_EMAIL_TO",
    ):
        monkeypatch.delenv(var, raising=False)

    cfg = ea.load_email_config()
    assert cfg["sender_email"] == "owner@example.com"
    assert cfg["sender_password"] == "abcd efgh ijkl mnop"
    # Digest defaults to the sending account rather than being dropped.
    assert cfg["recipient_emails"] == ["owner@example.com"]
