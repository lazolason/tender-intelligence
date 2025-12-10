# ==========================================================
# TRANSNET SCRAPER
# Scrapes tenders from Transnet's procurement portal
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

from utils.text_cleaner import clean_text, extract_closing_date_from_text
from classify_engine import classify_tender


def scrape_transnet():
    """
    Scrape tenders from Transnet
    Source: Transnet's official tender/RFQ portal
    """
    tenders = []
    
    try:
        print("🔍 Scraping Transnet tenders...")
        
        # Transnet tenders on National Treasury e-Tender portal
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
            "departments": "Transnet"
        }
        
        response = requests.post(url, data=params, headers=headers, timeout=10, verify=False)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.content, "html.parser")
        
        # Look for tender/RFQ links
        tender_links = soup.find_all("a", href=re.compile(r"(tender|rfq|bid|download|document)", re.I))
        
        for link in tender_links:
            try:
                title = link.get_text(strip=True)
                
                if len(title) < 5:
                    continue
                
                href = link.get("href", "")
                
                if not href:
                    continue
                
                if not href.startswith("http"):
                    href = "https://www.transnet.net" + href if href.startswith("/") else "https://www.transnet.net/" + href
                
                # Extract reference number
                ref_match = re.search(r"(TN|TNT|TRANSNET)[\s\-]?(\d+)", title, re.I)
                ref = f"{ref_match.group(1)}-{ref_match.group(2)}" if ref_match else f"TN-{len(tenders)+1}"
                
                # Parse closing date
                closing_date = extract_closing_date_from_text(title)
                
                tender = {
                    "ref": ref,
                    "source": "Transnet",
                    "url": href,
                    "title": title,
                    "short_title": title[:50],
                    "description": title,
                    "client": "Transnet",
                    "category": "Logistics",
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
        
        print(f"   ✅ Transnet: {len(tenders)} tenders found")
        return tenders
        
    except Exception as e:
        print(f"   ❌ Transnet scraper error: {e}")
        traceback.print_exc()
        return []


if __name__ == "__main__":
    tenders = scrape_transnet()
    print(json.dumps(tenders, indent=2))
