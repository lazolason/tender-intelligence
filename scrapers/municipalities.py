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

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_cleaner import clean_text
from classify_engine import classify_tender


class BaseMunicipalityScraper:
    """Base class for municipality scrapers"""
    
    def __init__(self, name: str, url: str, timeout: int = 15):
        self.name = name
        self.url = url
        self.timeout = timeout
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
    
    def fetch_page(self):
        try:
            response = requests.get(self.url, headers=self.headers, timeout=self.timeout, verify=False)
            response.raise_for_status()
            return response.text
        except Exception as e:
            raise Exception(f"Error fetching {self.name}: {e}")
    
    def parse_tenders(self, html: str):
        """Override in subclass"""
        raise NotImplementedError
    
    def run(self):
        try:
            html = self.fetch_page()
            return self.parse_tenders(html)
        except Exception as e:
            # Gracefully ignore availability errors (e.g., 404s) and return empty
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
# CITY OF TSHWANE
# ===========================================================
class TshwaneScraper(BaseMunicipalityScraper):
    
    def __init__(self, timeout: int = 15):
        super().__init__(
            name="City of Tshwane",
            url="https://www.tshwane.gov.za/sites/Departments/Financial-Services/Pages/Aborwa-Tenders.aspx",
            timeout=timeout
        )
    
    def parse_tenders(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        tenders = []
        
        # Tshwane uses SharePoint-style lists
        for selector in ["table tbody tr", ".ms-listviewtable tr", ".tender", "li"]:
            rows = soup.select(selector)
            if rows:
                break
        
        for row in rows:
            try:
                cells = row.find_all("td")
                if len(cells) < 2:
                    link = row.find("a")
                    if link:
                        title = clean_text(link.get_text())
                    else:
                        continue
                else:
                    title = clean_text(cells[1].get_text()) if len(cells) > 1 else clean_text(cells[0].get_text())
                    ref = clean_text(cells[0].get_text()) if cells else "TSH"
                
                if not title or len(title) < 10:
                    continue
                
                classification = classify_tender(title, title)
                
                tenders.append({
                    "ref": ref if 'ref' in locals() else "TSH",
                    "title": title,
                    "short_title": classification["short_title"],
                    "client": "City of Tshwane",
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
# ETHEKWINI MUNICIPALITY
# ===========================================================
class EthekwiniScraper(BaseMunicipalityScraper):
    
    def __init__(self, timeout: int = 15):
        super().__init__(
            name="eThekwini Municipality",
            url="https://www.durban.gov.za/pages/government/tenders",
            timeout=timeout
        )
    
    def parse_tenders(self, html: str):
        soup = BeautifulSoup(html, "html.parser")
        tenders = []
        
        for selector in ["table tbody tr", ".tender", "article", ".content-item"]:
            rows = soup.select(selector)
            if rows:
                break
        
        for row in rows:
            try:
                link = row.find("a")
                title = clean_text(link.get_text()) if link else clean_text(row.get_text())
                
                if not title or len(title) < 10:
                    continue
                
                classification = classify_tender(title, title)
                
                tenders.append({
                    "ref": "ETH",
                    "title": title,
                    "short_title": classification["short_title"],
                    "client": "eThekwini Municipality",
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
def scrape_all_municipalities(timeout: int = 15):
    """Run all municipality scrapers and aggregate results"""
    
    scrapers = [
        EkurhuleniScraper(timeout),
        TshwaneScraper(timeout),
        CapeTownScraper(timeout),
        EthekwiniScraper(timeout),
    ]
    
    all_tenders = []
    
    for scraper in scrapers:
        try:
            print(f"Scraping {scraper.name}...")
            tenders = scraper.run()
            all_tenders.extend(tenders)
            print(f"  Found {len(tenders)} tenders")
        except Exception as e:
            print(f"  Error: {e}")
            continue
    
    return all_tenders


# ===========================================================
# STANDALONE TEST
# ===========================================================
if __name__ == "__main__":
    tenders = scrape_all_municipalities()
    print(f"\n Total: {len(tenders)} tenders from municipalities")
    
    for t in tenders[:10]:
        print(f"  [{t['source']}] {t['ref']}: {t['title'][:50]}... → {t['category']}")
