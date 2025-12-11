# ==========================================================
# ESKOM DIRECT TENDER SCRAPER
# Scrapes tenders from Eskom's own tender bulletin portal
# https://www.eskom.co.za/Tenders/
# ==========================================================

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.chrome.options import Options
from datetime import datetime
import time
import traceback
import sys
import re
import os

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender


def scrape_eskom_tenders(max_tenders=50):
    """
    Scrape tenders directly from Eskom's tender bulletin portal
    """
    tenders = []
    driver = None
    
    try:
        print(f"\n🔍 Scraping Eskom tenders from Eskom Tender Bulletin...")
        
        # Chrome options
        chrome_options = Options()
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        chromedriver_path = '/opt/homebrew/bin/chromedriver'
        if not os.path.exists(chromedriver_path):
            chromedriver_path = None
        
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to Eskom tender bulletin - use search page which has all opportunities
        # Use large page size to get all tenders at once (they have ~60-80 active tenders)
        url = "https://tenderbulletin.eskom.co.za/search?pageSize=100&page=1"
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 20)
        time.sleep(8)  # Wait longer for React app to render
        
        print(f"   Page loaded: {driver.title}")
        
        # Wait for content to render
        try:
            wait.until(lambda d: d.find_elements(By.CSS_SELECTOR, "button, h2, h3, p, [role='heading']"))
            print(f"   Content loaded")
        except:
            print(f"   ⚠️ Content did not load as expected")
        
        # Scrape multiple pages
        page_num = 1
        max_pages = 5  # Limit to prevent infinite loops
        
        while page_num <= max_pages and len(tenders) < max_tenders:
            print(f"   📄 Scraping page {page_num}...")
            
            time.sleep(3)  # Wait for page content
            
            # Look for current tender opportunities section
            try:
                # Find tender cards/rows - React apps use various divs
                tender_elements = driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='tender'], [class*='opportunity'], div[role='article'], li")
                print(f"   Found {len(tender_elements)} potential tender elements")
                
                if len(tender_elements) == 0:
                    # Try to get page source to debug
                    page_source = driver.page_source
                    if "Current Tender" in page_source or "opportunity" in page_source.lower():
                        print(f"   Page contains tender information in HTML but not easily selectable")
                        # Try extracting from page source with regex
                        refs = re.findall(r'[A-Z]{2,}/\d{4}/[A-Z0-9]{2,}', page_source)
                        if refs:
                            print(f"   Found {len(set(refs))} reference numbers in page source: {set(refs)}")
            
            except Exception as e:
                print(f"   Error finding tender elements: {e}")
                break
            
            # Extract tender information from current page
            count_this_page = 0
            for idx, element in enumerate(tender_elements):
                try:
                    # Get all text from element
                    element_text = element.text.strip()
                    
                    # DEBUG: Print first element on first page
                    if idx == 0 and page_num == 1:
                        print(f"   Element {idx+1} text (first 100 chars): {element_text[:100]}")
                    
                    if not element_text or len(element_text) < 15:
                        continue
                    
                    # Look for reference number (e.g., E2253GXGPLET, ERI/2022/BMS/08, MWP2457DX, etc.)
                    ref_match = re.search(r'[A-Z]\d{4}[A-Z]{2,}[A-Z0-9]+|[A-Z]{2,}/\d{4}/[A-Z0-9]{2,}|[A-Z]{3}\d{4}[A-Z]{2}', element_text)
                    if not ref_match:
                        continue
                    
                    ref = ref_match.group(0).strip()
                    
                    # Skip if already have this tender
                    if any(t["ref"] == ref for t in tenders):
                        continue
                    
                    print(f"   Found ref: {ref}")
                    
                    # Get title - usually first substantial text line
                    lines = element_text.split('\n')
                    title = ""
                    for line in lines:
                        clean_line = line.strip()
                        if len(clean_line) > 15 and not clean_line.startswith(ref) and not clean_line.isdigit():
                            title = clean_line
                            break
                    
                    if not title or len(title) < 15:
                        title = element_text[:100]
                    
                    # Try to find link
                    try:
                        link_elem = element.find_element(By.TAG_NAME, "a")
                        href = link_elem.get_attribute("href")
                        if not href.startswith("http"):
                            href = "https://tenderbulletin.eskom.co.za" + href if href.startswith("/") else "https://tenderbulletin.eskom.co.za/"
                    except:
                        href = "https://tenderbulletin.eskom.co.za/"
                    
                    # Extract closing date if visible
                    closing_date = ""
                    date_match = re.search(r'\d{4}-[A-Z][a-z]{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}\s+[A-Z][a-z]{2}\s+\d{4}', element_text)
                    if date_match:
                        closing_date = date_match.group(0)
                    
                    tender = {
                        "ref": ref,
                        "source": "Eskom",
                        "url": href,
                        "title": title[:100],
                        "short_title": title[:50],
                        "description": element_text[:500],
                        "client": "Eskom",
                        "category": "Unknown",
                        "closing_date": closing_date,
                        "scraped_date": datetime.now().isoformat()
                    }
                    
                    # Classify
                    classification = classify_tender(title[:100], element_text[:500])
                    tender["category"] = classification["category"]
                    tender["reason"] = classification.get("reason", "")
                    
                    tenders.append(tender)
                    count_this_page += 1
                    print(f"   ✓ Tender {len(tenders)}: {ref} - {title[:50]}")
                    
                    if len(tenders) >= max_tenders:
                        break
                
                except Exception as e:
                    if idx < 3 and page_num == 1:
                        print(f"   Error extracting element {idx+1}: {e}")
                    continue
            
            print(f"   Found {count_this_page} tenders on page {page_num}")
            
            # Navigate to next page by URL
            if len(tenders) < max_tenders:
                try:
                    page_num += 1
                    next_url = f"https://tenderbulletin.eskom.co.za/search?pageSize=20&page={page_num}"
                    print(f"   Loading page {page_num}...")
                    driver.get(next_url)
                    time.sleep(5)  # Wait for page to load
                    
                    # Check if we got new content (page exists)
                    page_source = driver.page_source
                    if "No tenders" in page_source or "No results" in page_source or len(driver.find_elements(By.CSS_SELECTOR, "[class*='card'], [class*='tender']")) == 0:
                        print(f"   Reached last page")
                        break
                except Exception as e:
                    print(f"   Could not navigate to next page: {e}")
                    break
            else:
                break
        
        driver.quit()
        
    except Exception as e:
        print(f"   ⚠️ Error scraping Eskom: {e}")
        traceback.print_exc()
        if driver:
            driver.quit()
    
    print(f"✅ Eskom: {len(tenders)} tenders found\n")
    return tenders


if __name__ == "__main__":
    tenders = scrape_eskom_tenders(max_tenders=20)
    for tender in tenders:
        print(tender)
