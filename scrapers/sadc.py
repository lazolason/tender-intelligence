# ==========================================================
# SADC REGIONAL SCRAPERS
# Botswana, Namibia
# ==========================================================

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classify_engine import classify_tender


def _is_excluded_category(value):
    """Return True when a classifier result should be skipped by the scraper."""
    return str(value or "").strip().upper() in {"EXCLUDED", "EXCLUDE"}
from utils.retry_tools import safe_get

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
}

def _scrape_sadc_generic(country, url, row_selector, ref_prefix):
    """Generic SADC scraper"""
    tenders = []
    
    try:
        resp = safe_get(url, headers=HEADERS, timeout=30, log=logger)
        if resp is None:
            raise RuntimeError(f"{country}: Failed to fetch page")

        soup = BeautifulSoup(resp.text, "html.parser")
        rows = soup.select(row_selector) or soup.select("table tr") or soup.select(".tender-item")
        
        for row in rows:
            text = row.get_text(" ", strip=True)
            if len(text) < 20: continue
            
            # Extract links
            link = row.find("a")
            href = link.get("href", "") if link else ""
            full_url = href if href.startswith("http") else f"{'/'.join(url.split('/')[:3])}/{href.lstrip('/')}" if href else url

            # 1. Closing Date
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
            closing = date_match.group(1) if date_match else ""
            
            # 2. Ref
            ref_match = re.search(r'([A-Z0-9]{3,}-?[\d/]{3,})', text)
            ref = ref_match.group(1) if ref_match else f"{ref_prefix}-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
            
            # 3. Title/Desc
            title = text[:200]
            
            classification = classify_tender(title, text)
            if not _is_excluded_category(classification["category"]):
                tenders.append({
                    "ref": ref,
                    "title": title,
                    "description": text[:500],
                    "client": f"{country} Tender",
                    "closing_date": closing,
                    "category": classification["category"],
                    "short_title": classification.get("short_title", "Tender"),
                    "reason": classification.get("reason", ""),
                    "source": country,
                    "url": full_url
                })
                
    except Exception as e:
        print(f"    ❌ {country} error: {e}")
        
    return tenders

# ------------------------------------------------
# BOTSWANA - etender.co.bw
# ------------------------------------------------
def scrape_botswana():
    return _scrape_sadc_generic(
        country="Botswana",
        url="https://etender.co.bw/botswana-tenders/",
        row_selector=".tender-list-item, table tr, article",
        ref_prefix="BW"
    )

# ------------------------------------------------
# NAMIBIA - namibiatenders.com (Aggregator)
# Note: This often requires login, fallback to generic parsing
# ------------------------------------------------
def scrape_namibia():
    return _scrape_sadc_generic(
        country="Namibia",
        url="https://www.namibiatenders.com/tenders", # Public listing page
        row_selector=".views-row, table tr",
        ref_prefix="NAM"
    )

def scrape_all_sadc():
    """Scrape all SADC sources"""
    all_tenders = []
    scrapers = [
        ("Botswana", scrape_botswana),
        ("Namibia", scrape_namibia),
    ]
    
    print("\n🌍 Scraping SADC Region...")
    for name, scraper in scrapers:
        print(f"  ... {name}")
        try:
            results = scraper()
            all_tenders.extend(results)
            if results:
                print(f"    ✅ Found {len(results)} tenders")
            else:
                print(f"    ⚠️ No tenders/connection")
        except Exception as e:
            print(f"    ❌ Failed: {e}")
            
    return all_tenders

if __name__ == "__main__":
    tenders = scrape_all_sadc()
    for t in tenders[:5]:
        print(f"[{t['source']}] {t['title'][:50]}...")
