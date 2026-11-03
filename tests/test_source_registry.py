"""Registry guards after retiring eTenders-duplicated scrapers.

Rand Water, Johannesburg Water, Transnet and Harmony Gold are covered by the
National Treasury eTenders feed (149 / 11 / 9 / 2 records on 2026-11-03).
Anglo American and Seriti appear in neither eTenders nor their own procurement
pages. None of them should be scraped again.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scrapers.soes as soes
from scrapers.registry import get_active_scrapers, SCRAPER_REGISTRY

RETIRED = (
    "scrape_rand_water",
    "scrape_transnet",
    "scrape_joburg_water_selenium",
    "scrape_harmony_gold",
    "scrape_anglo_american",
    "scrape_seriti",
)
ACTIVE = ("scrape_eskom",)


def test_retired_sources_are_not_scraped(monkeypatch):
    called = []

    for name in ACTIVE:
        monkeypatch.setattr(soes, name, lambda n=name: (called.append(n), [])[1])
    for name in RETIRED:
        monkeypatch.setattr(soes, name, lambda n=name: (called.append(f"RETIRED:{n}"), [])[1])

    soes.scrape_all_soes()

    assert [c for c in called if c.startswith("RETIRED:")] == []
    assert set(called) == set(ACTIVE)


def test_retired_functions_still_exist_for_reference():
    """Removed from the registry, not deleted, so history stays readable."""
    for name in RETIRED:
        assert hasattr(soes, name), f"{name} should remain defined"


def test_registry_has_no_johannesburg_water_entry():
    names = [registration.name for registration in SCRAPER_REGISTRY]
    assert "Johannesburg Water" not in names
    # eTenders remains the canonical source for it.
    assert "National Treasury" in names


def test_selenium_mode_does_not_reintroduce_johannesburg_water():
    names = [getattr(scraper, "source_name", None) for scraper in get_active_scrapers(enable_selenium=True)]
    assert "Johannesburg Water" not in names
