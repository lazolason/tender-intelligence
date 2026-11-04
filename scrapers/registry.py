"""Explicit scraper registry for the tender pipeline."""

from typing import List

from scrapers.base import BaseScraper, ScraperRegistration
from scrapers.municipalities import scrape_all_municipalities
from scrapers.water_boards import scrape_all_water_boards


def _scrape_national_treasury() -> list:
    from scrapers.national_treasury import NationalTreasuryScraper

    return NationalTreasuryScraper().run()


def _scrape_eskom_bulletin() -> list:
    from scrapers.eskom_direct import scrape_eskom_tenders

    return scrape_eskom_tenders()


SCRAPER_REGISTRY = [
    ScraperRegistration(
        name="National Treasury",
        scrape_func=_scrape_national_treasury,
        description="Primary full eTenders feed, including SOE adverts",
    ),
    ScraperRegistration(
        name="Municipalities",
        scrape_func=lambda: scrape_all_municipalities(raise_on_error=True),
        description="Supplementary City of Cape Town direct portal",
    ),
    ScraperRegistration(
        name="Water Boards",
        scrape_func=lambda: scrape_all_water_boards(raise_on_error=True),
        description="South African water board sources",
    ),
    # Johannesburg Water is intentionally absent: its tenders page redirects to
    # eTenders, which the National Treasury registration above already ingests
    # (11 records on 2026-11-03). Scraping it directly only duplicated coverage.
    ScraperRegistration(
        name="Eskom Tender Bulletin",
        scrape_func=_scrape_eskom_bulletin,
        requires_selenium=False,
        description="Eskom bulletin API with Selenium fallback",
    ),
]


def get_active_scrapers(*, enable_selenium: bool) -> List[BaseScraper]:
    """Return the active scraper instances for the current runtime configuration."""
    return [
        registration.build()
        for registration in SCRAPER_REGISTRY
        if enable_selenium or not registration.requires_selenium
    ]
