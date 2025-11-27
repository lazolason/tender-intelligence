# ==========================================================
# SOE (STATE-OWNED ENTERPRISES) SCRAPERS v3.1
# Updated 27 November 2025 - FIXED URLs from screenshots
# ==========================================================

import requests
from bs4 import BeautifulSoup
from datetime import datetime
import re
import sys
import os
import urllib3

# Suppress SSL warnings
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classify_engine import classify_tender

# Import Selenium version for Johannesburg Water
try:
    from scrapers.joburg_water_selenium import scrape_joburg_water_selenium
except ImportError:
    def scrape_joburg_water_selenium():
        return []
try:
    from scrapers.joburg_water_selenium import scrape_joburg_water_selenium
except ImportError:
    scrape_joburg_water_selenium = lambda: []


HEADERS = {
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
    "Accept-Language": "en-US,en;q=0.5",
}

# ----------------------------------------------------------
# RAND WATER - CORRECT URL: randwater.co.za/availabletenders.php
# ----------------------------------------------------------
def scrape_rand_water():
    """Scrape Rand Water tenders from the CORRECT URL"""
    tenders = []
    
    # THE ACTUAL URL from screenshot
    url = "https://www.randwater.co.za/availabletenders.php"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find the tender table - structure from screenshot
            table = soup.find("table")
            if table:
                rows = table.find_all("tr")[1:]  # Skip header row
                
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 4:
                        # Column structure: Title | Description | Closing Date | Contact | Notices
                        title_cell = cols[0]
                        desc_cell = cols[1]
                        date_cell = cols[2]
                        contact_cell = cols[3] if len(cols) > 3 else None
                        
                        # Get title and link
                        title_link = title_cell.find("a")
                        title = title_link.get_text(strip=True) if title_link else title_cell.get_text(strip=True)
                        tender_url = title_link.get("href") if title_link else ""
                        
                        # Extract reference from title (e.g., RW10397693/25RR)
                        ref_match = re.search(r'(RW\d+[-/]?\d*\w*)', title)
                        ref = ref_match.group(1) if ref_match else f"RW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                        
                        # Get description
                        description = desc_cell.get_text(strip=True) if desc_cell else ""
                        
                        # Get closing date
                        closing = date_cell.get_text(strip=True) if date_cell else ""
                        
                        # Get contact
                        contact = contact_cell.get_text(strip=True) if contact_cell else ""
                        
                        # Full URL
                        if tender_url and not tender_url.startswith("http"):
                            tender_url = f"https://www.randwater.co.za/{tender_url}"
                        
                        # Classify
                        full_text = f"{title} {description}"
                        classification = classify_tender(title, description)
                        
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref,
                                "title": f"{title} - {description[:100]}",
                                "description": description,
                                "client": "Rand Water",
                                "closing_date": closing,
                                "contact": contact,
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Rand Water",
                                "url": tender_url or url
                            })
            
            # Also check for pagination (Page: 1 Page: 2 Page: 3)
            pagination = soup.select("a[href*='page']")
            for page_link in pagination[:3]:  # Check first 3 pages
                page_url = page_link.get("href", "")
                if page_url and page_url != url:
                    if not page_url.startswith("http"):
                        page_url = f"https://www.randwater.co.za/{page_url}"
                    try:
                        page_resp = requests.get(page_url, headers=HEADERS, timeout=15, verify=False)
                        if page_resp.status_code == 200:
                            page_soup = BeautifulSoup(page_resp.text, "html.parser")
                            page_table = page_soup.find("table")
                            if page_table:
                                page_rows = page_table.find_all("tr")[1:]
                                for row in page_rows:
                                    cols = row.find_all("td")
                                    if len(cols) >= 3:
                                        title_cell = cols[0]
                                        desc_cell = cols[1]
                                        date_cell = cols[2]
                                        
                                        title_link = title_cell.find("a")
                                        title = title_link.get_text(strip=True) if title_link else title_cell.get_text(strip=True)
                                        
                                        ref_match = re.search(r'(RW\d+[-/]?\d*\w*)', title)
                                        ref = ref_match.group(1) if ref_match else f"RW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                                        
                                        description = desc_cell.get_text(strip=True) if desc_cell else ""
                                        closing = date_cell.get_text(strip=True) if date_cell else ""
                                        
                                        classification = classify_tender(title, description)
                                        if classification["category"] != "Exclude" and ref not in [t["ref"] for t in tenders]:
                                            tenders.append({
                                                "ref": ref,
                                                "title": f"{title} - {description[:100]}",
                                                "description": description,
                                                "client": "Rand Water",
                                                "closing_date": closing,
                                                "category": classification["category"],
                                                "short_title": classification.get("short_title", "Tender"),
                                                "reason": classification.get("reason", ""),
                                                "source": "Rand Water",
                                                "url": page_url
                                            })
                    except:
                        pass
                        
    except Exception as e:
        print(f"    Rand Water error: {e}")
    
    return tenders

# ----------------------------------------------------------
# JOHANNESBURG WATER - CORRECT URL: johannesburgwater.co.za/tenders/
# DataTables structure with tabs
# ----------------------------------------------------------
def scrape_joburg_water():
    """Scrape Johannesburg Water tenders"""
    tenders = []
    
    # THE ACTUAL URL from screenshot
    url = "https://www.johannesburgwater.co.za/tenders/"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # Find the DataTable - structure from screenshot
            # Columns: Category | TENDER DESCRIPTION | ESUBMISSION | ADVERTISED | CLOSING
            table = soup.find("table")
            if table:
                rows = table.find_all("tr")[1:]  # Skip header
                
                for row in rows:
                    cols = row.find_all("td")
                    if len(cols) >= 5:
                        category = cols[0].get_text(strip=True)
                        description = cols[1].get_text(strip=True)
                        esubmission = cols[2].get_text(strip=True) if len(cols) > 2 else ""
                        advertised = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                        closing = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                        
                        # Generate reference
                        ref_match = re.search(r'(JW[-/]?\d{4,}|COJ[-/]?\d+)', description)
                        ref = ref_match.group(1) if ref_match else f"JW-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                        
                        # Parse closing date (format: "in X days")
                        days_match = re.search(r'in (\d+) days?', closing)
                        if days_match:
                            from datetime import timedelta
                            days = int(days_match.group(1))
                            close_date = datetime.now() + timedelta(days=days)
                            closing = close_date.strftime("%Y-%m-%d")
                        
                        # Classify
                        classification = classify_tender(description, f"{category} {description}")
                        
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref,
                                "title": description[:150],
                                "description": f"Category: {category}. {description}",
                                "client": "Johannesburg Water",
                                "closing_date": closing,
                                "advertised": advertised,
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Johannesburg Water",
                                "url": url
                            })
                            
    except Exception as e:
        print(f"    Johannesburg Water error: {e}")
    
    return tenders

# ----------------------------------------------------------
# TRANSNET - Uses eTenders (etenders.gov.za)
# ----------------------------------------------------------
def scrape_transnet():
    """Scrape Transnet tenders from eTenders portal"""
    tenders = []
    
    # Transnet uses the National Treasury eTenders portal
    url = "https://www.etenders.gov.za/Home/opportunities?TextSearch=transnet"
    
    try:
        resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
        
        if resp.status_code == 200:
            soup = BeautifulSoup(resp.text, "html.parser")
            
            # eTenders structure
            rows = soup.select("table tr, .tender-item, .opportunity-item, article")
            
            for row in rows:
                text = row.get_text(" ", strip=True)
                if len(text) < 30 or "transnet" not in text.lower():
                    continue
                
                # Extract reference
                ref_match = re.search(r'(TNT[-/]?\d{4,}|TRN[-/]?\d{4,}|HOAC[-/]?\d+|[A-Z]{2,5}[-/]\d{4,})', text)
                ref = ref_match.group(1) if ref_match else f"TNT-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                
                # Extract date
                date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4}|\d{1,2}\s+\w+\s+\d{4})', text)
                closing = date_match.group(1) if date_match else ""
                
                title = text[:200]
                
                classification = classify_tender(title, text)
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
                        "source": "Transnet",
                        "url": url
                    })
                    
    except Exception as e:
        print(f"    Transnet error: {e}")
    
    # Deduplicate
    seen = set()
    unique = []
    for t in tenders:
        if t["ref"] not in seen:
            seen.add(t["ref"])
            unique.append(t)
    
    return unique

# ----------------------------------------------------------
# ESKOM - Multiple URL strategies
# ----------------------------------------------------------
def scrape_eskom():
    """Scrape Eskom tenders"""
    tenders = []
    
    urls = [
        "https://www.eskom.co.za/eskom-tenders/",
        "https://www.eskom.co.za/procurement/tenders/",
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Check for PDF links
                pdf_links = soup.select("a[href$='.pdf']")
                for link in pdf_links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    
                    if any(kw in text.lower() or kw in href.lower() for kw in ["tender", "rfq", "rfp", "bid"]):
                        ref_match = re.search(r'(ESK[-/]?\d{4,}|MWP[-/]?\d{4,}|RFQ[-/]?\d+)', text + href)
                        ref = ref_match.group(1) if ref_match else f"ESK-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                        
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        closing = date_match.group(1) if date_match else ""
                        
                        title = text if text else href.split("/")[-1].replace(".pdf", "")
                        full_url = href if href.startswith("http") else f"https://www.eskom.co.za{href}"
                        
                        classification = classify_tender(title, title)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref,
                                "title": title[:150],
                                "description": f"Eskom tender: {title}",
                                "client": "Eskom",
                                "closing_date": closing,
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Eskom",
                                "url": full_url
                            })
                
                # Check table rows
                rows = soup.select("table tr, .tender-item, article")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    
                    ref_match = re.search(r'(ESK[-/]?\d{4,}|MWP[-/]?\d{4,}|RFQ[-/]?\d+)', text)
                    if ref_match:
                        ref = ref_match.group(1)
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        closing = date_match.group(1) if date_match else ""
                        
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref,
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Eskom",
                                "closing_date": closing,
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Eskom",
                                "url": url
                            })
                
                if tenders:
                    break
                    
        except Exception as e:
            print(f"    Eskom error: {e}")
    
    # Deduplicate
    seen = set()
    unique = []
    for t in tenders:
        if t["ref"] not in seen:
            seen.add(t["ref"])
            unique.append(t)
    
    return unique

# ----------------------------------------------------------
# SANRAL
# ----------------------------------------------------------
def scrape_sanral():
    """Scrape SANRAL tenders"""
    tenders = []
    
    urls = [
        "https://www.nra.co.za/live/tenders.php",
        "https://www.sanral.co.za/tenders/",
    ]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                
                # Check for tender links
                links = soup.select("a[href*='tender'], a[href$='.pdf']")
                for link in links:
                    href = link.get("href", "")
                    text = link.get_text(strip=True)
                    
                    if len(text) > 10:
                        ref_match = re.search(r'(SANRAL[-/]?\d+|NRA[-/]?\d+|[A-Z]{1,3}[-/]?\d{3,})', text + href)
                        ref = ref_match.group(1) if ref_match else f"SANRAL-{datetime.now().strftime('%Y%m%d')}-{len(tenders)+1}"
                        
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        closing = date_match.group(1) if date_match else ""
                        
                        full_url = href if href.startswith("http") else f"{url.rsplit('/', 1)[0]}/{href}"
                        
                        classification = classify_tender(text, text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref,
                                "title": text[:150],
                                "description": f"SANRAL tender: {text}",
                                "client": "SANRAL",
                                "closing_date": closing,
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "SANRAL",
                                "url": full_url
                            })
                
                if tenders:
                    break
                    
        except Exception as e:
            print(f"    SANRAL error: {e}")
    
    return tenders

# ----------------------------------------------------------
# UMGENI WATER
# ----------------------------------------------------------
def scrape_umgeni_water():
    tenders = []
    urls = ["https://www.umgeni.co.za/tenders/", "https://www.umgeni.co.za/procurement/"]
    
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article, a[href$='.pdf']")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(UW[-/]?\d{4,}|UMGENI[-/]?\d+)', text)
                    if ref_match:
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Umgeni Water",
                                "closing_date": date_match.group(1) if date_match else "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Umgeni Water",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# SASOL
# ----------------------------------------------------------
def scrape_sasol():
    tenders = []
    urls = ["https://www.sasol.com/procurement", "https://www.sasol.com/suppliers"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article, .card")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(SAS[-/]?\d{4,}|SASOL[-/]?\d+)', text)
                    if ref_match:
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Sasol",
                                "closing_date": date_match.group(1) if date_match else "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Sasol",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# SANEDI
# ----------------------------------------------------------
def scrape_sanedi():
    tenders = []
    urls = ["https://www.sanedi.org.za/tenders/", "https://www.sanedi.org.za/procurement/"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article, .post")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(SANEDI[-/]?\d{4,}|SAN[-/]?\d{4,})', text)
                    if ref_match:
                        date_match = re.search(r'(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})', text)
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "SANEDI",
                                "closing_date": date_match.group(1) if date_match else "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "SANEDI",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# ANGLO AMERICAN
# ----------------------------------------------------------
def scrape_anglo_american():
    tenders = []
    urls = ["https://www.angloamerican.com/suppliers"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(AAP[-/]?\d{4,}|ANGLO[-/]?\d{4,})', text)
                    if ref_match:
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Anglo American",
                                "closing_date": "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Anglo American",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# HARMONY GOLD
# ----------------------------------------------------------
def scrape_harmony_gold():
    tenders = []
    urls = ["https://www.harmony.co.za/business/procurement"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(HAR[-/]?\d{4,}|HMY[-/]?\d{4,})', text)
                    if ref_match:
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Harmony Gold",
                                "closing_date": "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Harmony Gold",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# SERITI RESOURCES
# ----------------------------------------------------------
def scrape_seriti():
    tenders = []
    urls = ["https://www.seritiza.com/procurement/"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(SER[-/]?\d{4,}|SERITI[-/]?\d{4,})', text)
                    if ref_match:
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Seriti Resources",
                                "closing_date": "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Seriti",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# EXXARO
# ----------------------------------------------------------
def scrape_exxaro():
    tenders = []
    urls = ["https://www.exxaro.com/suppliers/"]
    for url in urls:
        try:
            resp = requests.get(url, headers=HEADERS, timeout=20, verify=False)
            if resp.status_code == 200:
                soup = BeautifulSoup(resp.text, "html.parser")
                rows = soup.select("table tr, .tender-item, article")
                for row in rows:
                    text = row.get_text(" ", strip=True)
                    if len(text) < 20:
                        continue
                    ref_match = re.search(r'(EXX[-/]?\d{4,}|EXXARO[-/]?\d{4,})', text)
                    if ref_match:
                        classification = classify_tender(text[:150], text)
                        if classification["category"] != "Exclude":
                            tenders.append({
                                "ref": ref_match.group(1),
                                "title": text[:150],
                                "description": text[:500],
                                "client": "Exxaro",
                                "closing_date": "",
                                "category": classification["category"],
                                "short_title": classification.get("short_title", "Tender"),
                                "reason": classification.get("reason", ""),
                                "source": "Exxaro",
                                "url": url
                            })
                if tenders:
                    break
        except:
            continue
    return tenders

# ----------------------------------------------------------
# MASTER FUNCTION
# ----------------------------------------------------------
def scrape_all_soes():
    """Scrape all SOE and corporate sources"""
    all_tenders = []
    
    scrapers = [
        ("Rand Water", scrape_rand_water),
        ("Johannesburg Water", scrape_joburg_water_selenium),
        ("Transnet", scrape_transnet),
        ("Eskom", scrape_eskom),
        ("SANRAL", scrape_sanral),
        ("Umgeni Water", scrape_umgeni_water),
        ("Sasol", scrape_sasol),
        ("SANEDI", scrape_sanedi),
        ("Anglo American", scrape_anglo_american),
        ("Harmony Gold", scrape_harmony_gold),
        ("Seriti", scrape_seriti),
        ("Exxaro", scrape_exxaro),
    ]
    
    for name, scraper in scrapers:
        print(f"  📡 Scraping {name}...")
        try:
            results = scraper()
            all_tenders.extend(results)
            if results:
                print(f"    ✅ Found {len(results)} tenders")
            else:
                print(f"    ⚠️ No tenders found")
        except Exception as e:
            print(f"    ❌ Error: {e}")
    
    return all_tenders


if __name__ == "__main__":
    print("=" * 60)
    print("🔍 Testing SOE Scrapers v3.1")
    print("=" * 60)
    
    tenders = scrape_all_soes()
    
    print("\n" + "=" * 60)
    print(f"📊 Total SOE tenders found: {len(tenders)}")
    print("=" * 60)
    
    if tenders:
        print("\n📋 Sample tenders:")
        for t in tenders[:10]:
            print(f"  [{t['source']}] {t['ref']}: {t['title'][:50]}...")
            if t.get('closing_date'):
                print(f"       Closing: {t['closing_date']}")

# Import and use Selenium version for Johannesburg Water
try:
    from scrapers.joburg_water_selenium import scrape_joburg_water_selenium
    # Override the basic scraper with Selenium version
    scrape_joburg_water = scrape_joburg_water_selenium
except ImportError:
    pass  # Use the basic version if Selenium import fails
