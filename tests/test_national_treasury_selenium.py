from scrapers import national_treasury_selenium as nt


def test_make_tender_ref_extracts_embedded_reference():
    scraper = nt.NationalTreasuryScraper(headless=True)

    ref = scraper._make_tender_ref(
        "Tender BSM 93/26: TECHNICAL ASSISTANCE AND INDEPENDENT ACCOUNTING REVIEW",
        fallback_parts=("technical assistance",),
    )

    assert ref == "BSM93/26"


def test_make_tender_ref_uses_stable_hashed_fallback():
    scraper = nt.NationalTreasuryScraper(headless=True)

    ref_a = scraper._make_tender_ref(
        "RFQ Workplace Readiness Workshop",
        fallback_parts=("RFQ Workplace Readiness Workshop", "National Treasury"),
    )
    ref_b = scraper._make_tender_ref(
        "RFQ Workplace Readiness Workshop",
        fallback_parts=("RFQ Workplace Readiness Workshop", "National Treasury"),
    )
    ref_c = scraper._make_tender_ref(
        "RFQ Socio Economic Impact Assessment System",
        fallback_parts=("RFQ Socio Economic Impact Assessment System", "National Treasury"),
    )

    assert ref_a == ref_b
    assert ref_a.startswith("NT-")
    assert ref_c.startswith("NT-")
    assert ref_a != ref_c


def test_setup_driver_falls_back_to_selenium_manager_when_local_driver_missing(monkeypatch):
    class FakeOptions:
        def __init__(self):
            self.arguments = []

        def add_argument(self, argument):
            self.arguments.append(argument)

    class FakeWebDriverModule:
        @staticmethod
        def Chrome(service=None, options=None):
            return created.setdefault("driver", FakeChrome(service=service, options=options))

    class FakeChrome:
        def __init__(self, service=None, options=None):
            self.service = service
            self.options = options
            self.timeout = None

        def set_page_load_timeout(self, timeout):
            self.timeout = timeout

    scraper = nt.NationalTreasuryScraper(headless=True)
    created = {}

    monkeypatch.setattr(nt, "verify_driver_alignment", lambda: (False, "146", None, "missing"))
    monkeypatch.setattr(nt, "setup_environment", lambda: None)
    monkeypatch.setattr(nt, "get_driver_path", lambda: None)
    monkeypatch.setattr(nt, "webdriver", FakeWebDriverModule)
    monkeypatch.setattr(nt, "Options", FakeOptions)

    scraper._setup_driver()

    assert created["driver"].service is None
    assert created["driver"].timeout == 30


def test_setup_driver_uses_local_service_when_driver_is_aligned(monkeypatch):
    class FakeOptions:
        def __init__(self):
            self.arguments = []

        def add_argument(self, argument):
            self.arguments.append(argument)

    class FakeWebDriverModule:
        @staticmethod
        def Chrome(service=None, options=None):
            return created.setdefault("driver", FakeChrome(service=service, options=options))

    class FakeChrome:
        def __init__(self, service=None, options=None):
            self.service = service
            self.options = options
            self.timeout = None

        def set_page_load_timeout(self, timeout):
            self.timeout = timeout

    scraper = nt.NationalTreasuryScraper(headless=True)
    created = {}

    monkeypatch.setattr(nt, "verify_driver_alignment", lambda: (True, "146", "146", "aligned"))
    monkeypatch.setattr(nt, "setup_environment", lambda: None)
    monkeypatch.setattr(nt, "get_driver_path", lambda: "/tmp/chromedriver")
    monkeypatch.setattr(nt, "Service", lambda path: {"path": path})
    monkeypatch.setattr(nt, "webdriver", FakeWebDriverModule)
    monkeypatch.setattr(nt, "Options", FakeOptions)

    scraper._setup_driver()

    assert created["driver"].service == {"path": "/tmp/chromedriver"}
    assert created["driver"].timeout == 30
