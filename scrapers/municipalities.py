# ==========================================================
# MUNICIPALITY TENDER SCRAPERS
# Static HTML scrapers for SA municipalities
# ==========================================================

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import traceback
import sys
import os
import logging
from typing import List, Dict, Optional

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_cleaner import clean_text
from utils.retry_tools import safe_get
from scrapers.base import PartialScrapeError
from classify_engine import classify_tender

logger = logging.getLogger(__name__)


class BaseMunicipalityScraper:
    """Base class for municipality scrapers"""
    
    def __init__(self, name: str, url: str, timeout: int = 15) -> None:
        self.name = name
        self.url = url
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        self.last_error: Optional[str] = None
    
    def fetch_page(self) -> str:
        """Fetch HTML content from scraper URL
        
        Returns:
            HTML content as string
            
        Raises:
            RuntimeError: If no response is returned
            Exception: If fetching fails
        """
        try:
            response = safe_get(
                self.url,
                headers=self.headers,
                timeout=self.timeout,
                log=logger,
            )
            if response is None:
                raise RuntimeError("No response returned")
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Error fetching {self.name}: {e}")
    
    def parse_tenders(self, html: str) -> List[Dict[str, any]]:
        """Parse HTML content to extract tender information
        
        Args:
            html: HTML content as string
            
        Returns:
            List of tender dictionaries
            
        Raises:
            NotImplementedError: If not overridden in subclass
        """
        raise NotImplementedError
    
    def run(self) -> List[Dict[str, any]]:
        """Execute scraper: fetch page and parse tenders
        
        Returns:
            List of tender dictionaries (empty list if error occurs)
        """
        try:
            self.last_error = None
            html = self.fetch_page()
            return self.parse_tenders(html)
        except Exception as e:
            # Gracefully ignore availability errors (e.g., 404s) and return empty
            self.last_error = str(e)
            logger.warning("%s scraper error: %s", self.name, e)
            return []


# ===========================================================
# CITY OF CAPE TOWN
# ===========================================================
class CapeTownScraper(BaseMunicipalityScraper):
    
    def __init__(self, timeout: int = 15):
        super().__init__(
            name="City of Cape Town",
            # The old "Work and business/.../Current-tenders" path returns HTTP
            # 404 (verified 2026-11-03); the procurement portal below serves the
            # live listing as a plain table with 40+ rows.
            url="https://web1.capetown.gov.za/web1/tenderportal/Tender",
            timeout=timeout
        )
    
    def parse_tenders(self, html: str):
        """Parse the procurement portal's tender table.

        Header layout (2026-11-03):
        Tender Number | Description | Directorate | Department | Closing Date | ...
        """
        soup = BeautifulSoup(html, "html.parser")
        table = soup.find("table")
        if table is None:
            return []

        rows = table.find_all("tr")
        if len(rows) < 2:
            return []

        header = [c.get_text(" ", strip=True).lower() for c in rows[0].find_all(["th", "td"])]

        def column(*prefixes):
            for prefix in prefixes:
                for index, name in enumerate(header):
                    if name.startswith(prefix):
                        return index
            return None

        i_ref = column("tender number", "tender no", "reference")
        i_desc = column("description", "title")
        i_dept = column("department", "directorate")
        i_close = column("closing date", "closing")

        tenders = []
        for row in rows[1:]:
            cells = [c.get_text(" ", strip=True) for c in row.find_all("td")]
            if not cells:
                continue

            def cell(index):
                return cells[index] if index is not None and index < len(cells) else ""

            ref = cell(i_ref) or "CPT"
            description = cell(i_desc)
            if not description or len(description) < 5:
                continue

            department = cell(i_dept)
            closing_date = cell(i_close)
            summary = f"{description} ({department})" if department else description

            classification = classify_tender(summary, description)

            tenders.append({
                "ref": ref,
                "title": description,
                "short_title": classification["short_title"],
                "client": "City of Cape Town",
                "closing_date": closing_date,
                "description": summary,
                "category": classification["category"],
                "reason": classification["reason"],
                "source": self.name
            })

        return tenders


# ===========================================================
# AGGREGATOR - RUN ALL MUNICIPALITIES
# ===========================================================
def scrape_all_municipalities(timeout: int = 15, *, raise_on_error: bool = False) -> List[Dict[str, any]]:
    """Run all municipality scrapers and aggregate results
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        List of tender dictionaries from all municipalities
    """
    scrapers = [
        CapeTownScraper(timeout),
    ]
    
    all_tenders: List[Dict[str, any]] = []
    failed_sources: Dict[str, str] = {}
    
    for scraper in scrapers:
        try:
            logger.info("Scraping %s...", scraper.name)
            tenders = scraper.run()
            all_tenders.extend(tenders)
            logger.info("%s: found %d tenders", scraper.name, len(tenders))
            if scraper.last_error:
                failed_sources[scraper.name] = scraper.last_error
        except Exception as e:
            logger.warning("%s failed: %s", scraper.name, e)
            failed_sources[scraper.name] = str(e)
            continue
    
    if failed_sources:
        logger.warning(
            "Failed municipality sources: %s", ", ".join(sorted(set(failed_sources)))
        )
        if raise_on_error:
            raise PartialScrapeError(all_tenders, failed_sources)
    
    return all_tenders


# ===========================================================
# STANDALONE TEST
# ===========================================================
if __name__ == "__main__":
    tenders = scrape_all_municipalities()
    print(f"\n Total: {len(tenders)} tenders from municipalities")
    
    for t in tenders[:10]:
        print(f"  [{t['source']}] {t['ref']}: {t['title'][:50]}... → {t['category']}")
