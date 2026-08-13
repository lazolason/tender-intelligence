from pathlib import Path

from scrapers import soes, water_boards


class FakeResponse:
    def __init__(self, text: str):
        self.text = text


def _read_fixture(name: str) -> str:
    fixtures_dir = Path(__file__).resolve().parent / "fixtures"
    return (fixtures_dir / name).read_text(encoding="utf-8")


def test_rand_water_fixture_parses_and_filters_non_mexel(monkeypatch):
    fixture_html = _read_fixture("rand_water_tenders.html")

    def fake_safe_get(url, **kwargs):
        assert "randwater" in url.lower()
        return FakeResponse(fixture_html)

    monkeypatch.setattr(soes, "safe_get", fake_safe_get)

    tenders = soes.scrape_rand_water()

    assert len(tenders) == 1
    tender = tenders[0]
    assert tender["ref"].startswith("RW10397693")
    assert tender["client"] == "Rand Water"
    assert tender["source"] == "Rand Water"
    assert tender["category"] == "MEXEL"
    assert tender["url"].endswith("/docs/RW10397693-26RR.pdf")


def test_generic_water_board_fixture_parses_and_filters_non_mexel(monkeypatch):
    fixture_html = _read_fixture("water_board_tenders.html")

    def fake_safe_get(url, **kwargs):
        assert "example-water-board" in url
        return FakeResponse(fixture_html)

    monkeypatch.setattr(water_boards, "safe_get", fake_safe_get)

    tenders = water_boards._scrape_generic_water_board(
        client_name="Example Water Board",
        url="https://example-water-board.local/tenders",
        row_selector="table#tenderTable tr",
        ref_prefix="EWB",
    )

    assert len(tenders) == 1
    tender = tenders[0]
    assert tender["ref"].startswith("UW-2026-001")
    assert tender["client"] == "Example Water Board"
    assert tender["source"] == "Example Water Board"
    assert tender["category"] == "MEXEL"
    assert tender["closing_date"] == "2026-05-15"
