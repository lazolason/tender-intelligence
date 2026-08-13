# ==========================================================
# WATER BOARDS SCRAPERS
# Implemented: Umgeni (uMngeni-uThukela), Magalies, Lepelle
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
from utils.retry_tools import safe_get

logger = logging.getLogger(__name__)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}


def _is_excluded_category(value):
    """Return True when a classifier result should be skipped by the scraper."""
    return str(value or "").strip().upper() in {"EXCLUDED", "EXCLUDE"}

def _scrape_generic_water_board(client_name, url, row_selector, ref_prefix):
    """Generic scraper for Water Boards with standard HTML tables"""
    tenders = []
    
    try:
        resp = safe_get(url, headers=HEADERS, timeout=30, log=logger)
        if resp is None:
            raise RuntimeError(f"{client_name}: Failed to fetch page")

        soup = BeautifulSoup(resp.text, "html.parser")
        
        # Try finding standard tables or list items
        rows = soup.select(row_selector)
        
        # Fallback: if no specific selector rows found, try generic table rows
        if not rows:
            rows = soup.select("table tr")
            
        for row in rows:
            # Get all text from row
            text = row.get_text(" ", strip=True)
            if len(text) < 20: 
                continue
                
            # Skip headers (usually "Description", "Date", "Closing")
            if "closing date" in text.lower() and len(text) < 100:
                continue

            # Check for generic tender links
            links = row.find_all("a")
            file_url = ""
            for link in links:
                href = link.get("href", "")
                if ".pdf" in href or "download" in href:
                    file_url = href if href.startswith("http") else f"{'/'.join(url.split('/')[:3])}{href}"
                    break
            
            # 1. Tender Reference extraction
            # Look for typical formats: XXX/2025, REF-123, etc.
            ref_pattern = r'([A-Z0-9]{2,}(?:[-/][A-Z0-9]+)+)'
            ref_match = re.search(ref_pattern, text)
            
            # If explicit prefix required/found
            if ref_match:
                ref = ref_match.group(1)
            else:
                # Generate if missing
                ref = f"{ref_prefix}-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                
            # 2. Closing Date extraction
            # Matches: 2025-10-12, 12 Oct 2025, 12/10/2025
            date_match = re.search(r'(\d{4}[-/]\d{1,2}[-/]\d{1,2}|\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+[A-Za-z]{3,}\s+\d{4})', text)
            closing = date_match.group(1) if date_match else ""
            
            # Cleanup Ref to avoid date confusion
            if closing and closing in ref:
                ref = f"{ref_prefix}-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
            
            # 3. Description/Title
            # Use text, but limit length
            title = text[:200]
            description = text[:500]
            
            # Classify
            classification = classify_tender(title, description)
            if not _is_excluded_category(classification["category"]):
                tenders.append({
                    "ref": ref,
                    "title": title,
                    "description": description,
                    "client": client_name,
                    "closing_date": closing,
                    "category": classification["category"],
                    "short_title": classification.get("short_title", "Tender"),
                    "reason": classification.get("reason", ""),
                    "source": client_name,
                    "url": file_url or url
                })
                
    except Exception as e:
        logger.warning("%s scrape failed: %s", client_name, e)
        
    return tenders

# ----------------------------------------------------------
# UMGENI WATER (uMngeni-uThukela)
# ----------------------------------------------------------
def scrape_umgeni_water():
    """Scrape Umgeni Water tenders"""
    return _scrape_generic_water_board(
        client_name="Umgeni Water",
        url="https://www.umngeni-uthukela.co.za/tender/",
        row_selector="table#tenderTable tr, table tr", # Specific ID often used
        ref_prefix="UW"
    )

# ----------------------------------------------------------
# MAGALIES WATER
# ----------------------------------------------------------
def scrape_magalies_water():
    """Scrape Magalies Water tenders"""
    return _scrape_generic_water_board(
        client_name="Magalies Water",
        url="https://magalieswater.co.za/tenders/",
        row_selector="table tr, .et_pb_text_inner p", # Divi builder often uses these
        ref_prefix="MW"
    )

# ----------------------------------------------------------
# LEPELLE NORTHERN WATER
# ----------------------------------------------------------
def scrape_lepelle_water():
    """Scrape Lepelle Northern Water tenders"""
    return _scrape_generic_water_board(
        client_name="Lepelle Northern Water",
        url="https://lepellewater.co.za/procurement/tenders/",
        row_selector="article, .entry-content p, table tr, .et_pb_text_inner p",
        ref_prefix="LNW"
    )

# ----------------------------------------------------------
# MASTER FUNCTION
# ----------------------------------------------------------
def scrape_all_water_boards():
    """Scrape all configured Water Boards"""
    all_tenders = []
    
    scrapers = [
        ("Umgeni Water", scrape_umgeni_water),
        ("Magalies Water", scrape_magalies_water),
        ("Lepelle Northern Water", scrape_lepelle_water),
    ]
    
    logger.info("Scraping water boards")
    
    for name, scraper in scrapers:
        logger.info("Running %s scraper", name)
        try:
            results = scraper()
            all_tenders.extend(results)
            if results:
                logger.info("%s: found %d tenders", name, len(results))
            else:
                logger.info("%s: no tenders found", name)
        except Exception as e:
            logger.warning("%s failed: %s", name, e)
            
    return all_tenders

if __name__ == "__main__":
    tenders = scrape_all_water_boards()
    for t in tenders[:5]:
        print(f"[{t['client']}] {t['title'][:50]}... ({t['closing_date']})")
