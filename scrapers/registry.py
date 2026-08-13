"""Explicit scraper registry for the tender pipeline."""

from typing import List

from scrapers.base import BaseScraper, ScraperRegistration
from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import scrape_all_soes
from scrapers.water_boards import scrape_all_water_boards


def _scrape_national_treasury() -> list:
    from scrapers.national_treasury import NationalTreasuryScraper

    return NationalTreasuryScraper().run()


def _scrape_joburg_water() -> list:
    from scrapers.joburg_water_selenium import scrape_joburg_water_selenium

    return scrape_joburg_water_selenium()


def _scrape_eskom_bulletin() -> list:
    from scrapers.eskom_direct import scrape_eskom_tenders

    return scrape_eskom_tenders()


SCRAPER_REGISTRY = [
    ScraperRegistration(
        name="Municipalities",
        scrape_func=scrape_all_municipalities,
        description="Static municipality tender pages",
    ),
    ScraperRegistration(
        name="SOEs",
        scrape_func=scrape_all_soes,
        description="State-owned enterprises and large corporate sources",
    ),
    ScraperRegistration(
        name="Water Boards",
        scrape_func=scrape_all_water_boards,
        description="South African water board sources",
    ),
    ScraperRegistration(
        name="National Treasury",
        scrape_func=_scrape_national_treasury,
        requires_selenium=False,
        description="Public National Treasury eTender listing feed",
    ),
    ScraperRegistration(
        name="Johannesburg Water",
        scrape_func=_scrape_joburg_water,
        requires_selenium=True,
        description="Selenium-driven Johannesburg Water scraping",
    ),
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
