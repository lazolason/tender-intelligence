from unittest.mock import Mock

import pytest

from scrapers.national_treasury import NationalTreasuryScraper
from scrapers.registry import get_active_scrapers


def _response(payload):
    response = Mock()
    response.json.return_value = payload
    response.raise_for_status.return_value = None
    return response


def test_fetches_public_listing_feed_with_bounded_pagination(monkeypatch):
    pages = [
        {
            "recordsTotal": 3,
            "recordsFiltered": 3,
            "data": [
                {"tender_No": "NT-1", "description": "Tender one"},
                {"tender_No": "NT-2", "description": "Tender two"},
            ],
        },
        {
            "recordsTotal": 3,
            "recordsFiltered": 3,
            "data": [{"tender_No": "NT-3", "description": "Tender three"}],
        },
    ]
    calls = []

    def fake_safe_get(url, **kwargs):
        calls.append((url, kwargs))
        return _response(pages.pop(0))

    monkeypatch.setattr("scrapers.national_treasury.safe_get", fake_safe_get)
    scraper = NationalTreasuryScraper(page_size=2)

    rows = scraper.fetch_all()

    assert [row["tender_No"] for row in rows] == ["NT-1", "NT-2", "NT-3"]
    assert [call[1]["params"]["start"] for call in calls] == [0, 2]
    assert all(call[0].endswith("/Home/PaginatedTenderOpportunities") for call in calls)
    assert all(call[1]["params"]["status"] == 1 for call in calls)


def test_parses_current_portal_field_names_without_classifying():
    scraper = NationalTreasuryScraper()
    tenders = scraper.parse_tenders(
        [
            {
                "tender_No": " HES 01/2026 ",
                "description": " Supply of cooling water treatment chemicals ",
                "organ_of_State": "Example Municipality",
                "category": "Supplies: General",
                "type": "Request for Bid(Open-Tender)",
                "conditions": "See documents",
                "closing_Date": "2026-09-18T12:00:00",
                "date_Published": "2026-08-13T00:00:00",
            }
        ]
    )

    assert tenders == [
        {
            "ref": "HES 01/2026",
            "title": "Supply of cooling water treatment chemicals",
            "description": (
                "Supply of cooling water treatment chemicals | Reference: HES 01/2026 | "
                "Supplies: General | Request for Bid(Open-Tender) | See documents"
            ),
            "client": "Example Municipality",
            "source": "National Treasury",
            "url": "https://www.etenders.gov.za/Home/opportunities",
            "closing_date": "2026-09-18",
            "published_date": "2026-08-13",
        }
    ]
    assert "category" not in tenders[0]


@pytest.mark.parametrize(
    "payload, message",
    [
        ([], "must be an object"),
        ({"recordsFiltered": 1}, "data array"),
        ({"recordsFiltered": "1", "data": []}, "record count"),
        ({"recordsFiltered": 1, "data": ["bad"]}, "non-object"),
    ],
)
def test_listing_structure_fails_closed(payload, message):
    with pytest.raises(ValueError, match=message):
        NationalTreasuryScraper._validate_page(payload)


def test_non_selenium_runtime_includes_public_treasury_feed():
    active_sources = {
        scraper.source_name for scraper in get_active_scrapers(enable_selenium=False)
    }

    assert "National Treasury" in active_sources
    assert "Johannesburg Water" not in active_sources


def test_pagination_refuses_truncation_and_excessive_snapshots(monkeypatch):
    monkeypatch.setattr(
        "scrapers.national_treasury.safe_get",
        lambda *args, **kwargs: _response({"recordsFiltered": 2, "data": []}),
    )
    with pytest.raises(ValueError, match="ended before"):
        NationalTreasuryScraper(page_size=1).fetch_all()

    monkeypatch.setattr(
        "scrapers.national_treasury.safe_get",
        lambda *args, **kwargs: _response({"recordsFiltered": 11, "data": []}),
    )
    with pytest.raises(ValueError, match="exceeds safety limit"):
        NationalTreasuryScraper(max_records=10).fetch_all()
