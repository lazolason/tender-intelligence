import os

import tenderscan


def test_runtime_path_uses_fallback_for_another_local_account(monkeypatch, tmp_path):
    fallback = tmp_path / "output"
    monkeypatch.delenv("OUTPUT_DIR", raising=False)

    path = tenderscan._portable_runtime_path(
        "OUTPUT_DIR",
        "/Users/another-account/Documents/tender-intelligence/output",
        str(fallback),
    )

    assert path == str(fallback)


def test_runtime_path_allows_an_explicit_override(monkeypatch, tmp_path):
    override = tmp_path / "custom-output"
    monkeypatch.setenv("OUTPUT_DIR", str(override))

    path = tenderscan._portable_runtime_path(
        "OUTPUT_DIR",
        "/Users/another-account/Documents/tender-intelligence/output",
        "/fallback/output",
    )

    assert path == str(override)


def test_runtime_path_keeps_external_path_when_its_root_exists(monkeypatch, tmp_path):
    configured = tmp_path / "external" / "output"
    monkeypatch.delenv("OUTPUT_DIR", raising=False)

    path = tenderscan._portable_runtime_path(
        "OUTPUT_DIR", str(configured), "/fallback/output"
    )

    assert path == os.path.abspath(configured)
