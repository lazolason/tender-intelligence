from tools import chromedriver_manager as manager


def test_verify_driver_alignment_reports_missing_driver(monkeypatch):
    monkeypatch.setattr(manager, "get_chrome_version", lambda: ("146", "146.0.7680.178", "/Applications/Google Chrome.app"))
    monkeypatch.setattr(manager, "get_installed_chromedriver_version", lambda: (None, None))
    monkeypatch.setattr(manager, "get_system_driver_path", lambda: None)

    aligned, chrome_major, driver_major, message = manager.verify_driver_alignment()

    assert aligned is False
    assert chrome_major == "146"
    assert driver_major is None
    assert "no chromedriver" in message.lower()


def test_verify_driver_alignment_accepts_matching_major_versions(monkeypatch):
    monkeypatch.setattr(manager, "get_chrome_version", lambda: ("146", "146.0.7680.178", "/Applications/Google Chrome.app"))
    monkeypatch.setattr(manager, "get_installed_chromedriver_version", lambda: ("146", "146.0.7680.72"))

    aligned, chrome_major, driver_major, message = manager.verify_driver_alignment()

    assert aligned is True
    assert chrome_major == "146"
    assert driver_major == "146"
    assert "aligned" in message.lower()
