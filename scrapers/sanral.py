# ==========================================================
# SANRAL SCRAPER
# Scrapes tenders from SANRAL (South African National Roads Agency)
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


def scrape_sanral():
    """
    Scrape tenders from SANRAL
    Source: SANRAL's official procurement portal
    """
    tenders = []
    
    try:
        print("🔍 Scraping SANRAL tenders...")
        
        # SANRAL tenders on National Treasury e-Tender portal
        url = "https://www.etenders.gov.za/Home/TenderOpportunities"
        
        headers = {
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest"
        }
        
        params = {
            "draw": 1,
            "start": 0,
            "length": 50,
            "tenderStatus": 1,
            "categories": "",
            "provinces": "",
            "departments": "SANRAL"
        }
        
        response = requests.post(url, data=params, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for tender items
        tender_items = soup.find_all("div", class_=re.compile(r"tender|item|post", re.I))
        
        if not tender_items:
            tender_items = soup.find_all("a", href=re.compile(r"(tender|rfq|document)", re.I))
        
        for item in tender_items:
            try:
                # Extract title
                title_elem = item.find(["h3", "h4", "span", "a"])
                title = title_elem.get_text(strip=True) if title_elem else item.get_text(strip=True)
                
                if len(title) < 5:
                    continue
                
                # Extract URL
                link = item.find("a")
                href = link.get("href", "") if link else ""
                
                if not href:
                    continue
                
                if not href.startswith("http"):
                    href = "https://www.sanral.co.za" + href if href.startswith("/") else "https://www.sanral.co.za/" + href
                
                # Extract reference number
                ref_match = re.search(r"(SANRAL)[\s\-]?(\d+)", title, re.I)
                ref = f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else f"SANRAL-{len(tenders)+1}"
                
                # Parse closing date
                closing_date = extract_closing_date_from_text(title)
                
                tender = {
                    "ref": ref,
                    "source": "SANRAL",
                    "url": href,
                    "title": title,
                    "short_title": title[:50],
                    "description": title,
                    "client": "SANRAL",
                    "category": "Infrastructure",
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
        
        print(f"   ✅ SANRAL: {len(tenders)} tenders found")
        return tenders
        
    except Exception as e:
        print(f"   ❌ SANRAL scraper error: {e}")
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
    tenders = scrape_sanral()
    print(json.dumps(tenders, indent=2))
