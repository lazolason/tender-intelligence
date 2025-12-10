# ==========================================================
# JOHANNESBURG WATER SCRAPER - Selenium Version
# DataTables content requires JavaScript rendering
# Captures direct PDF links from etenders.gov.za
# ==========================================================

import sys
import os
import re
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classify_engine import classify_tender

def scrape_joburg_water_selenium():
    """Scrape Johannesburg Water using Selenium for JS-rendered content"""
    tenders = []
    
    try:
        from selenium import webdriver
        from selenium.webdriver.chrome.options import Options
        import time
        
        options = Options()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        options.add_argument('--disable-gpu')
        
        driver = webdriver.Chrome(options=options)
        driver.set_page_load_timeout(30)
        
        url = "https://www.johannesburgwater.co.za/tenders/"
        driver.get(url)
        time.sleep(6)  # Wait for DataTable to load
        
        html = driver.page_source
        soup = BeautifulSoup(html, 'html.parser')
        
        # Build a map of tender refs to their PDF URLs from all links on page
        pdf_links = {}
        for link in soup.find_all('a', href=True):
            href = link['href']
            text = link.get_text(strip=True).upper()
            if '.pdf' in href.lower() and 'etenders.gov.za' in href:
                # Extract tender ref from link text (e.g., "JW 14402 CORRIDORS...")
                # Match patterns like: JW 14402, JW-14402, JW14402, RFQJW165NS25, JW CYD 015/24
                ref_patterns = [
                    r'(JW\s*CYD\s*\d+[/\-]?\d*)',  # JW CYD 015/24
                    r'(JW\s*OPS\s*\d+[/\-]?\d*)',  # JW OPS 077/24
                    r'(JW\s*CHR\s*\d+[/\-]?\d*)',  # JW CHR 001/25
                    r'(JW[\s\-]*\d{5})',            # JW 14402 or JW-14402
                    r'(RFQJW\w+)',                  # RFQJW165NS25
                ]
                for pattern in ref_patterns:
                    ref_match = re.search(pattern, text, re.IGNORECASE)
                    if ref_match:
                        ref_key = ref_match.group(1).upper()
                        # Normalize: remove dashes and extra spaces
                        ref_key = re.sub(r'[\-\s]+', ' ', ref_key).strip()
                        if ref_key not in pdf_links:
                            pdf_links[ref_key] = href
                        break
        
        # Get main table
        main_table = soup.find('table')
        
        if main_table:
            rows = main_table.find_all('tr')
            
            current_tender = {}
            
            for row in rows:
                cols = row.find_all('td')
                
                # Main data row has many columns (>5) - contains tender summary
                if len(cols) >= 5:
                    # Check if this is a header row (has "Category" text)
                    first_col = cols[0].get_text(strip=True)
                    if first_col and first_col not in ['Category', 'Details:']:
                        # This is a tender row
                        category = cols[0].get_text(strip=True)
                        description = cols[1].get_text(strip=True)
                        advertised = cols[3].get_text(strip=True) if len(cols) > 3 else ""
                        closing_text = cols[4].get_text(strip=True) if len(cols) > 4 else ""
                        
                        # Parse closing date (format: "in X days")
                        closing_date = ""
                        days_match = re.search(r'in (\d+) days?', closing_text)
                        if days_match:
                            days = int(days_match.group(1))
                            close_date = datetime.now() + timedelta(days=days)
                            closing_date = close_date.strftime("%Y-%m-%d")
                        
                        current_tender = {
                            "category": category,
                            "description": description,
                            "advertised": advertised,
                            "closing_date": closing_date,
                        }
                
                # Detail rows have 2 columns with label/value pairs
                elif len(cols) == 2:
                    label = cols[0].get_text(strip=True)
                    value = cols[1].get_text(strip=True)
                    
                    if "Tender Number" in label and current_tender:
                        ref = value
                        desc = current_tender.get("description", "")
                        cat = current_tender.get("category", "")
                        
                        # Find matching PDF URL
                        tender_url = url  # Default to main page
                        ref_normalized = re.sub(r'[\-\s]+', ' ', ref.upper()).strip()
                        
                        # Try exact match first, then partial
                        if ref_normalized in pdf_links:
                            tender_url = pdf_links[ref_normalized]
                        else:
                            # Try matching by first part (e.g., "JW 14402" from "JW 14402 RR")
                            for pdf_ref, pdf_url in pdf_links.items():
                                if pdf_ref in ref_normalized or ref_normalized.startswith(pdf_ref):
                                    tender_url = pdf_url
                                    break
                        
                        if desc:  # Only add if we have a description
                            classification = classify_tender(desc, f"{cat} {desc}")
                            
                            if classification["category"] != "Exclude":
                                tenders.append({
                                    "ref": ref,
                                    "title": desc[:150],
                                    "description": f"Category: {cat}. {desc}",
                                    "client": "Johannesburg Water",
                                    "closing_date": current_tender.get("closing_date", ""),
                                    "advertised": current_tender.get("advertised", ""),
                                    "category": classification["category"],
                                    "short_title": classification.get("short_title", "Tender"),
                                    "reason": classification.get("reason", ""),
                                    "source": "Johannesburg Water",
                                    "url": tender_url
                                })
                            
                            current_tender = {}  # Reset for next tender
                    
                    # Also capture actual closing date from details
                    elif "Closing Date" in label and current_tender and value:
                        # Format: 2026-02-20T10:30:00
                        date_match = re.search(r'(\d{4}-\d{2}-\d{2})', value)
                        if date_match:
                            current_tender["closing_date"] = date_match.group(1)
        
        driver.quit()
        
    except Exception as e:
        print(f"    Johannesburg Water Selenium error: {e}")
    
    # Deduplicate by reference
    seen = set()
    unique = []
    for t in tenders:
        if t["ref"] not in seen:
            seen.add(t["ref"])
            unique.append(t)
    
    return unique


if __name__ == "__main__":
    print("Testing Johannesburg Water Selenium scraper...")
    tenders = scrape_joburg_water_selenium()
    print(f"Found {len(tenders)} tenders\n")
    
    for t in tenders[:10]:
        print(f"  [{t['ref']}] {t['title'][:50]}...")
        print(f"       URL: {t['url'][:80]}...")
        print(f"       Closing: {t['closing_date']}")
        print()
