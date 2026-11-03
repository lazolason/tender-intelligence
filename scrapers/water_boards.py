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
def _magalies_date(raw: str) -> str:
    """Convert '27 November 2026 at 12:00' to ISO '2026-11-27'."""
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw or "")
    if not match:
        return ""
    try:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2)} {match.group(3)}", "%d %B %Y"
        ).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def scrape_magalies_water():
    """Scrape Magalies Water's Visual Composer toggle list.

    Each tender is a .vc_toggle block whose title holds the advert heading and
    whose content carries 'Contract No:', 'Closing Date:' and a PDF link. The
    generic row scraper found no table rows and therefore reported zero tenders.
    """
    url = "https://magalieswater.co.za/tenders/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    resp = safe_get(url, headers=headers, timeout=20, log=logger)
    if resp is None:
        logger.warning("Magalies Water: no response")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    blocks = soup.select(".vc_toggle")
    if not blocks:
        logger.warning("Magalies Water: no toggle blocks found")
        return []

    tenders = []
    for block in blocks:
        heading = block.select_one(".vc_toggle_title h4") or block.find("h4")
        title = heading.get_text(" ", strip=True) if heading else ""
        if not title or len(title) < 12:
            continue
        # Supplier-database forms and generic notices are not opportunities.
        if not any(word in title.upper() for word in ("TENDER", "RFQ", "RFB", "BID")):
            continue

        content = block.select_one(".vc_toggle_content")
        body = content.get_text(" ", strip=True) if content else ""

        ref_match = re.search(r"Contract\s*No[:.]?\s*([A-Za-z0-9/._\-]+)", body, re.IGNORECASE)
        ref = ref_match.group(1) if ref_match else f"MW-{len(tenders) + 1}"

        closing_match = re.search(
            r"Closing\s*Date[:.]?\s*(\d{1,2}\s+[A-Za-z]+\s+\d{4})", body, re.IGNORECASE
        )
        closing = _magalies_date(closing_match.group(1)) if closing_match else ""

        # The page keeps a long history. Ingesting closed adverts would count as
        # "new tenders" and fire alerts for dead opportunities.
        if closing and closing < datetime.now().strftime("%Y-%m-%d"):
            continue

        pdf = ""
        if content:
            for link in content.find_all("a", href=True):
                if ".pdf" in link["href"].lower():
                    pdf = link["href"]
                    break

        classification = classify_tender(title, body[:500])

        tenders.append({
            "ref": ref,
            "title": title,
            "description": (body[:500] or title),
            "client": "Magalies Water",
            "closing_date": closing,
            "category": classification["category"],
            "short_title": classification.get("short_title", "Tender"),
            "reason": classification.get("reason", ""),
            "source": "Magalies Water",
            "url": pdf,
        })

    logger.info("Magalies Water: %d tenders", len(tenders))
    return tenders

# ----------------------------------------------------------
# LEPELLE NORTHERN WATER
# ----------------------------------------------------------
def _lepelle_date(raw: str) -> str:
    """Convert '07 December 2026 11:00am' to ISO '2026-12-07'."""
    match = re.search(r"(\d{1,2})\s+([A-Za-z]+)\s+(\d{4})", raw or "")
    if not match:
        return ""
    try:
        return datetime.strptime(
            f"{match.group(1)} {match.group(2)} {match.group(3)}", "%d %B %Y"
        ).strftime("%Y-%m-%d")
    except ValueError:
        return ""


def scrape_lepelle_water():
    """Scrape Lepelle Northern Water from its article-based opportunity list.

    Each opportunity is <article class="alt-theme-opportunity"> with a bid number
    and a <dl> of opening/closing dates. The generic row scraper found no table
    rows and reported zero tenders.
    """
    url = "https://www.lepellewater.co.za/procurement/tenders/"
    headers = {"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"}

    resp = safe_get(url, headers=headers, timeout=20, log=logger)
    if resp is None:
        logger.warning("Lepelle Northern Water: no response")
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    articles = soup.select("article.alt-theme-opportunity")
    if not articles:
        logger.warning("Lepelle Northern Water: no opportunity articles found")
        return []

    tenders = []
    for article in articles:
        heading = article.find("h3")
        link = heading.find("a") if heading else None
        title = (link.get_text(" ", strip=True) if link else (heading.get_text(" ", strip=True) if heading else ""))
        if not title or len(title) < 10:
            continue

        reference_el = article.select_one(".alt-theme-opportunity__reference")
        ref = reference_el.get_text(" ", strip=True) if reference_el else ""
        ref = re.sub(r"(?i)^bid\s*number:\s*", "", ref).strip()

        closing = ""
        for fact in article.select("dl > div"):
            label = fact.find("dt")
            value = fact.find("dd")
            if label and value and "closing" in label.get_text(" ", strip=True).lower():
                closing = _lepelle_date(value.get_text(" ", strip=True))
                break

        classification = classify_tender(title, title)

        tenders.append({
            "ref": ref or f"LNW-{len(tenders) + 1}",
            "title": title,
            "description": title,
            "client": "Lepelle Northern Water",
            "closing_date": closing,
            "category": classification["category"],
            "short_title": classification.get("short_title", "Tender"),
            "reason": classification.get("reason", ""),
            "source": "Lepelle Northern Water",
            "url": link.get("href", "") if link else "",
        })

    logger.info("Lepelle Northern Water: %d tenders", len(tenders))
    return tenders

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
