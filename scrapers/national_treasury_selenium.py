#!/usr/bin/env python3
# ==========================================================
# NATIONAL TREASURY eTENDER SELENIUM SCRAPER
# Scrapes tenders from etenders.gov.za using Selenium
# ==========================================================

import os
import sys
import time
import re
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException

from classify_engine import classify_tender

# ==========================================================
# CONFIGURATION
# ==========================================================
ETENDER_URLS = [
    "https://www.etenders.gov.za/Home/opportunities",
    "https://www.etenders.gov.za/content/advertised-tenders"
]
MAX_PAGES = 3
WAIT_TIMEOUT = 20


class NationalTreasuryScraper:
    """Selenium scraper for National Treasury eTender portal"""
    
    def __init__(self, headless: bool = True):
        self.headless = headless
        self.driver = None
        self.tenders = []
    
    def _setup_driver(self):
        """Initialize Chrome WebDriver"""
        options = Options()
        
        if self.headless:
            options.add_argument("--headless")
        
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--window-size=1920,1080")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-notifications")
        options.add_argument("user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36")
        
        self.driver = webdriver.Chrome(options=options)
        self.driver.set_page_load_timeout(30)
    
    def _close_driver(self):
        """Close browser"""
        if self.driver:
            self.driver.quit()
            self.driver = None
    
    def _parse_closing_date(self, date_str: str) -> str:
        """Parse closing date to YYYY-MM-DD format"""
        if not date_str:
            return ""
        try:
            date_str = date_str.strip()
            
            # Try different formats
            for fmt in ["%d %b %Y", "%d %B %Y", "%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%d-%m-%Y"]:
                try:
                    dt = datetime.strptime(date_str, fmt)
                    return dt.strftime("%Y-%m-%d")
                except:
                    continue
            
            # Try to extract date with regex
            match = re.search(r'(\d{1,2})[/-](\d{1,2})[/-](\d{4})', date_str)
            if match:
                d, m, y = match.groups()
                return f"{y}-{m.zfill(2)}-{d.zfill(2)}"
            
            return date_str
        except:
            return ""
    
    def _scrape_opportunities_page(self) -> list:
        """Scrape the opportunities listing page"""
        tenders = []
        
        try:
            # Wait for content to load
            time.sleep(5)
            
            # Try to find tender cards/items
            # Look for common container patterns
            containers = self.driver.find_elements(By.CSS_SELECTOR, 
                ".tender-item, .opportunity-item, .card, .list-item, article, .row")
            
            print(f"   Found {len(containers)} potential containers")
            
            # Also try table rows
            rows = self.driver.find_elements(By.CSS_SELECTOR, "table tr, tbody tr")
            
            for row in rows[1:]:  # Skip header
                try:
                    cells = row.find_elements(By.TAG_NAME, "td")
                    if len(cells) >= 2:
                        # Extract text from cells
                        texts = [c.text.strip() for c in cells]
                        
                        # Find title (usually longest text)
                        title = max(texts, key=len) if texts else ""
                        
                        if len(title) > 15:
                            # Look for reference number pattern
                            ref = ""
                            for t in texts:
                                if re.match(r'^[A-Z]{2,5}[-/]?\d+', t):
                                    ref = t
                                    break
                            
                            # Look for client/department
                            client = ""
                            for t in texts:
                                if "department" in t.lower() or "municipality" in t.lower():
                                    client = t
                                    break
                            
                            # Look for date
                            closing = ""
                            for t in texts:
                                parsed = self._parse_closing_date(t)
                                if parsed:
                                    closing = parsed
                                    break
                            
                            classification = classify_tender(title, title)
                            
                            tenders.append({
                                "ref": ref or f"NT-{datetime.now().strftime('%H%M%S')}",
                                "title": title[:200],
                                "description": title,
                                "client": client or "National Treasury",
                                "closing_date": closing,
                                "category": classification["category"],
                                "reason": classification["reason"],
                                "short_title": classification["short_title"],
                                "source": "National Treasury"
                            })
                except:
                    continue
            
            # Try finding links that look like tender listings
            links = self.driver.find_elements(By.TAG_NAME, "a")
            for link in links:
                try:
                    href = link.get_attribute("href") or ""
                    text = link.text.strip()
                    
                    # Look for tender-related links
                    if len(text) > 30 and ("tender" in href.lower() or "bid" in href.lower() or "rfq" in href.lower()):
                        classification = classify_tender(text, text)
                        
                        tenders.append({
                            "ref": f"NT-{datetime.now().strftime('%H%M%S')}",
                            "title": text[:200],
                            "description": text,
                            "client": "National Treasury",
                            "closing_date": "",
                            "category": classification["category"],
                            "reason": classification["reason"],
                            "short_title": classification["short_title"],
                            "source": "National Treasury"
                        })
                except:
                    continue
                    
        except Exception as e:
            print(f"   ⚠️ Error: {e}")
        
        return tenders
    
    def scrape(self) -> list:
        """Main scraping function"""
        print("\n🏛️ National Treasury eTender Scraper")
        print("=" * 40)
        
        try:
            self._setup_driver()
            
            for url in ETENDER_URLS:
                print(f"\n🌐 Loading: {url}")
                
                try:
                    self.driver.get(url)
                    time.sleep(3)
                    
                    page_tenders = self._scrape_opportunities_page()
                    self.tenders.extend(page_tenders)
                    
                    print(f"   Found {len(page_tenders)} tenders")
                    
                except Exception as e:
                    print(f"   ⚠️ Failed to load: {e}")
                    continue
            
        except Exception as e:
            print(f"❌ Scraper error: {e}")
        
        finally:
            self._close_driver()
        
        # Remove duplicates
        seen = set()
        unique = []
        for t in self.tenders:
            key = t["title"][:50]
            if key not in seen:
                seen.add(key)
                unique.append(t)
        
        self.tenders = unique
        
        # Count relevant
        relevant = [t for t in self.tenders if t["category"] in ["TES", "Phakathi", "Both"]]
        
        print(f"\n📊 Results:")
        print(f"   Total scraped: {len(self.tenders)}")
        print(f"   TES/Phakathi:  {len(relevant)}")
        
        return self.tenders


def scrape_national_treasury() -> list:
    """Convenience function to scrape National Treasury"""
    scraper = NationalTreasuryScraper(headless=True)
    return scraper.scrape()


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    tenders = scrape_national_treasury()
    
    print("\n" + "=" * 60)
    print("SAMPLE TENDERS FOUND:")
    print("=" * 60)
    
    for t in tenders[:10]:
        print(f"\n📋 {t['ref']}")
        print(f"   Title: {t['title'][:70]}...")
        print(f"   Client: {t['client']}")
        print(f"   Category: {t['category']}")
        print(f"   Closing: {t['closing_date']}")
