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
                verify=False,
                log=logger,
            )
            if response is None:
                raise RuntimeError("No response returned")
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
            print(f"  Error: {e}")
            return []


# ===========================================================
# CITY OF EKURHULENI
# ===========================================================
class EkurhuleniScraper(BaseMunicipalityScraper):
    
    def __init__(self, timeout: int = 15):
        super().__init__(
            name="City of Ekurhuleni",
            url="https://www.ekurhuleni.gov.za/tenders/",
            timeout=timeout
        )
    
    def parse_tenders(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        tenders = []
        
        # Look for tender tables or lists
        for selector in ["table tbody tr", ".tender-item", "article", ".post"]:
            rows = soup.select(selector)
            if rows:
                break
        
        for row in rows:
            try:
                # Extract links and text
                link = row.find("a")
                title = clean_text(link.get_text()) if link else clean_text(row.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                # Try to find date
                date_elem = row.find(class_=lambda x: x and "date" in x.lower()) if row else None
                closing_date = clean_text(date_elem.get_text()) if date_elem else ""
                
                # Try to find reference
                ref_elem = row.find(class_=lambda x: x and ("ref" in x.lower() or "number" in x.lower())) if row else None
                ref = clean_text(ref_elem.get_text()) if ref_elem else "EKU"
                
                classification = classify_tender(title, title)
                
                tenders.append({
                    "ref": ref,
                    "title": title,
                    "short_title": classification["short_title"],
                    "client": "City of Ekurhuleni",
                    "closing_date": closing_date,
                    "description": title,
                    "category": classification["category"],
                    "reason": classification["reason"],
                    "source": self.name
                })
                
            except Exception:
                continue
        
        return tenders


# ===========================================================
# CITY OF CAPE TOWN
# ===========================================================
class CapeTownScraper(BaseMunicipalityScraper):
    
    def __init__(self, timeout: int = 15):
        super().__init__(
            name="City of Cape Town",
            url="https://www.capetown.gov.za/Work%20and%20business/Tenders-and-supplier-management/Tenders/Current-tenders",
            timeout=timeout
        )
    
    def parse_tenders(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        tenders = []
        
        # Cape Town uses accordion/list style
        for selector in [".accordion-item", ".tender-item", "table tbody tr", ".list-item", "article"]:
            rows = soup.select(selector)
            if rows:
                break
        
        for row in rows:
            try:
                link = row.find("a")
                title = clean_text(link.get_text()) if link else clean_text(row.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                # Look for tender number pattern
                import re
                ref_match = re.search(r'[A-Z]{2,4}[-/]?\d+[-/]?\d*', title)
                ref = ref_match.group(0) if ref_match else "CPT"
                
                classification = classify_tender(title, title)
                
                tenders.append({
                    "ref": ref,
                    "title": title,
                    "short_title": classification["short_title"],
                    "client": "City of Cape Town",
                    "closing_date": "",
                    "description": title,
                    "category": classification["category"],
                    "reason": classification["reason"],
                    "source": self.name
                })
                
            except Exception:
                continue
        
        return tenders


# ===========================================================
# AGGREGATOR - RUN ALL MUNICIPALITIES
# ===========================================================
def scrape_all_municipalities(timeout: int = 15) -> List[Dict[str, any]]:
    """Run all municipality scrapers and aggregate results
    
    Args:
        timeout: Request timeout in seconds
        
    Returns:
        List of tender dictionaries from all municipalities
    """
    scrapers = [
        EkurhuleniScraper(timeout),
        CapeTownScraper(timeout),
    ]
    
    all_tenders: List[Dict[str, any]] = []
    failed_sources: List[str] = []
    
    for scraper in scrapers:
        try:
            print(f"Scraping {scraper.name}...")
            tenders = scraper.run()
            all_tenders.extend(tenders)
            print(f"  Found {len(tenders)} tenders")
            if scraper.last_error:
                failed_sources.append(scraper.name)
        except Exception as e:
            print(f"  Error: {e}")
            failed_sources.append(scraper.name)
            continue
    
    if failed_sources:
        print(f"  ❌ Failed municipality sources: {', '.join(sorted(set(failed_sources)))}")
    
    return all_tenders


# ===========================================================
# STANDALONE TEST
# ===========================================================
if __name__ == "__main__":
    tenders = scrape_all_municipalities()
    print(f"\n Total: {len(tenders)} tenders from municipalities")
    
    for t in tenders[:10]:
        print(f"  [{t['source']}] {t['ref']}: {t['title'][:50]}... → {t['category']}")
