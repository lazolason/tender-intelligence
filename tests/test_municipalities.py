"""Cape Town parser tests. The live URL returned HTTP 404 until 2026-11-03, so
this pins the table shape the scraper now depends on."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scrapers.municipalities import CapeTownScraper

TABLE_HTML = """
<html><body>
<table>
  <tr>
    <th>Tender Number</th><th>Description</th><th>Directorate</th>
    <th>Department</th><th>Closing Date</th><th>Date Advertised</th>
  </tr>
  <tr>
    <td>80S/2026/27</td>
    <td>Calibration, maintenance and upgrade of electrical meters</td>
    <td>WATER AND SANITATION</td>
    <td>Water Services</td>
    <td>2026-11-03</td>
    <td>2026-10-01</td>
  </tr>
  <tr>
    <td>99S/2026/27</td>
    <td>Supply, installation and commissioning of urban cctv</td>
    <td>SAFETY</td>
    <td>Safety and Security</td>
    <td>2026-11-20</td>
    <td>2026-10-05</td>
  </tr>
</table>
</body></html>
"""


def test_parses_tender_table_columns():
    tenders = CapeTownScraper().parse_tenders(TABLE_HTML)
    assert len(tenders) == 2

    first = tenders[0]
    assert first["ref"] == "80S/2026/27"
    assert first["closing_date"] == "2026-11-03"
    assert first["title"].startswith("Calibration, maintenance")
    assert first["client"] == "City of Cape Town"
    assert first["source"] == "City of Cape Town"
    # Department is folded into the description used for classification.
    assert "Water Services" in first["description"]
    assert "category" in first and "reason" in first


def test_header_only_table_returns_no_tenders():
    html = "<table><tr><th>Tender Number</th><th>Description</th></tr></table>"
    assert CapeTownScraper().parse_tenders(html) == []


def test_page_without_table_returns_no_tenders():
    assert CapeTownScraper().parse_tenders("<html><body>no table here</body></html>") == []
