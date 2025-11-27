# ==========================================================
# SOE (STATE-OWNED ENTERPRISES) SCRAPERS
# Updated November 2025 with working URLs
# ==========================================================

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.classify import classify_tender

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
}

# ----------------------------------------------------------
# RAND WATER
# ----------------------------------------------------------
def scrape_rand_water():
    tenders = []
    urls = [
        "https://www.randwater.co.za/tenders",
        "https://www.randwater.co.za/procurement/tenders",
        "https://www.randwater.co.za/Pages/Tenders.aspx"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Try multiple selectors
                rows = soup.select("table tr, .tender-item, .procurement-item, article")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    # Look for tender patterns
                    ref_match = re.search(r'(RW[-/]?\d{4,}[-/]?\d*|[A-Z]{2,4}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"RW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    # Extract date
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    # Get title
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Rand Water",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Rand Water"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# TRANSNET
# ----------------------------------------------------------
def scrape_transnet():
    tenders = []
    urls = [
        "https://www.transnet.net/TenderPortal/Tenders",
        "https://www.transnet.net/BusinessWithUs/Tenders/Pages/Tenders.aspx",
        "https://www.transnet.net/Tenders"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table tr, .tender-row, .tender-item, article, .list-item")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(TNT[-/]?\d{4,}|TRN[-/]?\d{4,}|[A-Z]{2,4}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"TNT-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Transnet",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Transnet"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# ESKOM
# ----------------------------------------------------------
def scrape_eskom():
    tenders = []
    urls = [
        "https://www.eskom.co.za/procurement/tenders/",
        "https://www.eskom.co.za/tenders/",
        "https://tenderbulletin.eskom.co.za/"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table tr, .tender-item, article, .post, .entry")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(ESK[-/]?\d{4,}|MWP[-/]?\d{4,}|[A-Z]{2,5}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"ESK-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Eskom",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Eskom"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# JOHANNESBURG WATER
# ----------------------------------------------------------
def scrape_joburg_water():
    tenders = []
    urls = [
        "https://www.johannesburgwater.co.za/tenders/",
        "https://www.johannesburgwater.co.za/procurement/",
        "https://www.joburg.org.za/work_/Pages/Work%20with%20the%20City/Tenders/Tenders.aspx"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table tr, .tender-item, article, .list-item")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(JW[-/]?\d{4,}|COJ[-/]?\d{4,}|[A-Z]{2,4}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"JW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Johannesburg Water",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Johannesburg Water"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# UMGENI WATER (Additional major water utility)
# ----------------------------------------------------------
def scrape_umgeni_water():
    tenders = []
    urls = [
        "https://www.umgeni.co.za/tenders/",
        "https://www.umgeni.co.za/procurement/"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table tr, .tender-item, article")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(UW[-/]?\d{4,}|[A-Z]{2,4}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"UW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Umgeni Water",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Umgeni Water"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# SASOL (Major industrial client)
# ----------------------------------------------------------
def scrape_sasol():
    tenders = []
    urls = [
        "https://www.sasol.com/procurement",
        "https://www.sasol.com/suppliers"
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                rows = soup.select("table tr, .tender-item, article, .card")
                
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(SAS[-/]?\d{4,}|[A-Z]{2,4}[-/]\d{4,})', text)
                    ref = ref_match.group(1) if ref_match else f"SAS-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                    
                    date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                    closing = date_match.group(1) if date_match else ""
                    
                    title = text[:150] if len(text) > 150 else text
                    
                    classification = classify_tender(title)
                    if classification["category"] != "Exclude":
                        tenders.append({
                            "ref": ref,
                            "title": title,
                            "description": text[:500],
                            "client": "Sasol",
                            "closing_date": closing,
                            "category": classification["category"],
                            "short_title": classification.get("short_title", "Tender"),
                            "reason": classification.get("reason", ""),
                            "source": "Sasol"
                        })
                break
        except Exception as e:
            continue
    
    return tenders

# ----------------------------------------------------------
# MASTER FUNCTION
# ----------------------------------------------------------
def scrape_all_soes():
    all_tenders = []
    
    scrapers = [
        ("Rand Water", scrape_rand_water),
        ("Transnet", scrape_transnet),
        ("Eskom", scrape_eskom),
        ("Johannesburg Water", scrape_joburg_water),
        ("Umgeni Water", scrape_umgeni_water),
        ("Sasol", scrape_sasol),
    ]
    
    for name, scraper in scrapers:
        print(f"Scraping {name}...")
        try:
            results = scraper()
            all_tenders.extend(results)
            print(f"  Found {len(results)} tenders")
        except Exception as e:
            print(f"  Error: {e}")
    
    return all_tenders


if __name__ == "__main__":
    print("Testing SOE Scrapers...")
    tenders = scrape_all_soes()
    print(f"\nTotal SOE tenders: {len(tenders)}")
    for t in tenders[:5]:
        print(f"  - [{t['source']}] {t['ref']}: {t['title'][:60]}...")
