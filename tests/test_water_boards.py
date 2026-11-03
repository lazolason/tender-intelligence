"""Lepelle Northern Water parser tests.

The site changed from tables to <article class="alt-theme-opportunity"> blocks,
which the generic row scraper could not see. These tests pin that structure
without touching the network.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import scrapers.water_boards as water_boards

ARTICLE_HTML = """
<html><body>
<div class="alt-opportunity-list">
  <article class="alt-theme-opportunity">
    <header class="alt-theme-opportunity__header">
      <h3><a href="https://www.lepellewater.co.za/tender/lnw0426-27/">
        APPOINTMENT OF PHYSICAL SECURITY SERVICE PROVIDERS FOR LEPELLE NORTHERN WATER
      </a></h3>
      <p class="alt-theme-opportunity__reference">Bid Number: LNW04/26/27</p>
    </header>
    <dl class="alt-theme-opportunity__facts">
      <div><dt>Opening Date</dt><dd>30 October 2026 11:00am</dd></div>
      <div><dt>Closing Date</dt><dd>07 December 2026 11:00am</dd></div>
    </dl>
  </article>
  <article class="alt-theme-opportunity">
    <header class="alt-theme-opportunity__header">
      <h3><a href="https://www.lepellewater.co.za/tender/lnw0526-27/">
        PROVISION OF SHORT-TERM INSURANCE BROKERAGE SERVICES
      </a></h3>
      <p class="alt-theme-opportunity__reference">Bid Number: LNW05/26/27</p>
    </header>
    <dl class="alt-theme-opportunity__facts">
      <div><dt>Closing Date</dt><dd>13 November 2026 11:00am</dd></div>
    </dl>
  </article>
</div>
</body></html>
"""


class _FakeResponse:
    def __init__(self, text):
        self.text = text


def test_parses_article_opportunities(monkeypatch):
    monkeypatch.setattr(water_boards, "safe_get", lambda *a, **k: _FakeResponse(ARTICLE_HTML))

    tenders = water_boards.scrape_lepelle_water()
    assert len(tenders) == 2

    first = tenders[0]
    assert first["ref"] == "LNW04/26/27"
    assert first["closing_date"] == "2026-12-07"
    assert first["client"] == "Lepelle Northern Water"
    assert first["title"].startswith("APPOINTMENT OF PHYSICAL SECURITY")
    assert first["url"].endswith("/lnw0426-27/")


def test_missing_closing_date_does_not_crash(monkeypatch):
    html = ARTICLE_HTML.replace(
        "<div><dt>Closing Date</dt><dd>13 November 2026 11:00am</dd></div>", ""
    )
    monkeypatch.setattr(water_boards, "safe_get", lambda *a, **k: _FakeResponse(html))

    tenders = water_boards.scrape_lepelle_water()
    assert tenders[1]["closing_date"] == ""


def test_no_articles_returns_empty(monkeypatch):
    monkeypatch.setattr(water_boards, "safe_get", lambda *a, **k: _FakeResponse("<html></html>"))
    assert water_boards.scrape_lepelle_water() == []


def test_date_conversion():
    assert water_boards._lepelle_date("07 December 2026 11:00am") == "2026-12-07"
    assert water_boards._lepelle_date("1 October 2026 08:00am") == "2026-10-01"
    assert water_boards._lepelle_date("no date here") == ""


MAGALIES_HTML = """
<html><body>
<div class="vc_do_toggle vc_toggle">
  <div class="vc_toggle_title"><h4>TENDER ADVERT : CONSTRUCTION OF A NEW RESERVOIR</h4></div>
  <div class="vc_toggle_content">
    <p>Contract No: RFB/MW/ES-10/2026-27/01</p>
    <p>Closing Date: 27 December 2026 at 12:00</p>
    <p><a href="https://magalieswater.co.za/wp-content/uploads/2026/10/advert.pdf">Read More</a></p>
  </div>
</div>
<div class="vc_do_toggle vc_toggle">
  <div class="vc_toggle_title"><h4>TENDER ADVERT : OLD EXPIRED WORKS</h4></div>
  <div class="vc_toggle_content">
    <p>Contract No: RFB/MW/ES-01/2020-21/01</p>
    <p>Closing Date: 01 January 2020 at 12:00</p>
  </div>
</div>
<div class="vc_do_toggle vc_toggle">
  <div class="vc_toggle_title"><h4>SUPPLIER DATABASE REGISTRATION FORM</h4></div>
  <div class="vc_toggle_content"><p>Not an opportunity</p></div>
</div>
</body></html>
"""


def test_magalies_parses_open_tenders_only(monkeypatch):
    monkeypatch.setattr(water_boards, "safe_get", lambda *a, **k: _FakeResponse(MAGALIES_HTML))

    tenders = water_boards.scrape_magalies_water()
    # Expired advert and the supplier-database form are both dropped.
    assert len(tenders) == 1

    tender = tenders[0]
    assert tender["ref"] == "RFB/MW/ES-10/2026-27/01"
    assert tender["closing_date"] == "2026-12-27"
    assert tender["client"] == "Magalies Water"
    assert tender["url"].endswith("advert.pdf")


def test_magalies_date_conversion():
    assert water_boards._magalies_date("27 November 2026 at 12:00") == "2026-11-27"
    assert water_boards._magalies_date("garbage") == ""
