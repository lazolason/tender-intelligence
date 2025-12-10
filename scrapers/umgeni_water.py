# ==========================================================
# UMGENI WATER SCRAPER
# Scrapes tenders from Umgeni Water official website
# ==========================================================

import requests
from datetime import datetime
import traceback
import json
import re
from bs4 import BeautifulSoup

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_cleaner import clean_text
from classify_engine import classify_tender


def scrape_umgeni_water():
    """
    Scrape tenders from Umgeni Water
    Main sources:
    1. Tender notices page
    2. Request for quotations
    """
    tenders = []
    
    try:
        print("🔍 Scraping Umgeni Water tenders...")
        
        # Main tenders page
        url = "https://www.umgeniwatermb.co.za/business/tenders"
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
        }
        
        response = requests.get(url, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for tender links and tables
        tender_links = soup.find_all("a", href=re.compile(r"(tender|rfq|quotation)", re.I))
        
        for link in tender_links:
            try:
                title = link.get_text(strip=True)
                if len(title) < 5:
                    continue
                
                href = link.get("href", "")
                if not href.startswith("http"):
                    href = "https://www.umgeni.co.za" + href if href.startswith("/") else "https://www.umgeni.co.za/" + href
                
                # Extract reference number if available
                ref_match = re.search(r"(UW|UMGENI)[\s\-]?(\d+)", title, re.I)
                ref = f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else f"UW-{len(tenders)+1}"
                
                # Parse closing date from title or page
                closing_date = extract_closing_date_from_text(title)
                
                tender = {
                    "ref": ref,
                    "source": "Umgeni Water",
                    "url": href,
                    "title": title,
                    "short_title": title[:50],
                    "description": title,
                    "client": "Umgeni Water",
                    "category": "Water Supply",
                    "closing_date": closing_date,
                    "scraped_date": datetime.now().isoformat()
                }
                
                # Classify
                classification = classify_tender(tender)
                tender["category"] = classification["category"]
                tender["reason"] = classification.get("reason", "")
                
                tenders.append(tender)
                
            except Exception as e:
                pass
        
        print(f"   ✅ Umgeni Water: {len(tenders)} tenders found")
        return tenders
        
    except Exception as e:
        print(f"   ❌ Umgeni Water scraper error: {e}")
        traceback.print_exc()
        return []


def extract_closing_date_from_text(text):
    """Extract closing date from text"""
    date_pattern = r"(\d{1,2})\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{4})?"
    
    match = re.search(date_pattern, text, re.I)
    if match:
        try:
            day = match.group(1)
            month = match.group(2)
            year = match.group(3) or str(datetime.now().year)
            return f"{year}-{month}-{day}"
        except:
            return None
    return None


if __name__ == "__main__":
    tenders = scrape_umgeni_water()
    print(json.dumps(tenders, indent=2))
