# ==========================================================
# NATIONAL TREASURY eTENDERS SELENIUM SCRAPER
# Scrapes tenders from etenders.gov.za for specific organizations
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


def scrape_etenders_for_organization(org_name, org_id, max_tenders=20):
    """
    Scrape tenders from National Treasury eTenders portal for a specific organization
    Args:
        org_name: Organization name (e.g., "Eskom", "Umgeni Water")
        org_id: Organization ID in dropdown (e.g., "167" for Eskom)
        max_tenders: Maximum number of tenders to scrape
    """
    tenders = []
    driver = None
    
    try:
        print(f"🔍 Scraping {org_name} tenders from eTenders portal...")
        
        # Chrome options
        chrome_options = Options()
        # chrome_options.add_argument('--headless')  # Disable headless for debugging
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
        chrome_options.add_argument('--window-size=1920,1080')
        chrome_options.add_argument('user-agent=Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36')
        
        # Try to find chromedriver
        chromedriver_path = '/opt/homebrew/bin/chromedriver'
        if not os.path.exists(chromedriver_path):
            chromedriver_path = None  # Let Selenium find it
        
        if chromedriver_path:
            service = Service(chromedriver_path)
            driver = webdriver.Chrome(service=service, options=chrome_options)
        else:
            driver = webdriver.Chrome(options=chrome_options)
        
        # Navigate to eTenders opportunities page
        url = "https://www.etenders.gov.za/Home/opportunities"
        driver.get(url)
        
        # Wait for page to load
        wait = WebDriverWait(driver, 20)
        time.sleep(8)
        
        print(f"   Using search approach for {org_name}...")
        
        # Find the search box in the DataTable
        try:
            search_box = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "#tendeList_filter input[type='search']")))
            print(f"   Found search box")
            time.sleep(2)
            
            # Use JavaScript to set the value since the element might not be interactable
            driver.execute_script(f"arguments[0].value = '{org_name}'; arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));", search_box)
            print(f"   Typed '{org_name}' in search via JavaScript")
            time.sleep(5)  # Wait for DataTable to filter
            
        except Exception as e:
            print(f"   ⚠️ Could not find/use search box: {e}")
            return tenders
        
        time.sleep(2)
        
        # Find all tender rows after search
        tender_rows = driver.find_elements(By.CSS_SELECTOR, "#tendeList tbody tr")
        
        print(f"   Found {len(tender_rows)} rows matching '{org_name}'")
        
        if len(tender_rows) == 0:
            print(f"   ⚠️ No tenders found. Trying with partial name...")
            # Try with shorter keyword
            if ' ' in org_name:
                keyword = org_name.split()[0]
                driver.execute_script(f"arguments[0].value = '{keyword}'; arguments[0].dispatchEvent(new Event('input', {{ bubbles: true }}));", search_box)
                time.sleep(4)
                tender_rows = driver.find_elements(By.CSS_SELECTOR, "#tendeList tbody tr")
                print(f"   Found {len(tender_rows)} rows with '{keyword}'")
        
        # Extract tenders
        count = 0
        for idx, row in enumerate(tender_rows[:max_tenders]):
            try:
                row_class = row.get_attribute("class") or ""
                if "dataTables_empty" in row_class:
                    print(f"   No matching tenders found")
                    break
                
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 4:
                    continue
                
                # Extract visible data
                category = cells[1].text.strip() if len(cells) > 1 else ""
                title = cells[2].text.strip() if len(cells) > 2 else ""
                closing_date = cells[5].text.strip() if len(cells) > 5 else ""
                
                if not title or len(title) < 10:
                    continue
                
                # Try to find link
                try:
                    link_elem = cells[2].find_element(By.TAG_NAME, "a")
                    href = link_elem.get_attribute("href")
                except:
                    href = "https://www.etenders.gov.za/Home/opportunities"
                
                # Extract reference number from title
                ref = ""
                ref_match = re.search(r'[A-Z][0-9]{4}[A-Z0-9]+', title)
                if ref_match:
                    ref = ref_match.group(0)
                else:
                    # Try to extract from row HTML
                    row_html = row.get_attribute("outerHTML")
                    ref_match = re.search(r'[A-Z][0-9]{4}[A-Z0-9]+', row_html)
                    if ref_match:
                        ref = ref_match.group(0)
                    else:
                        ref = f"{org_name[:3].upper()}-{count+1}"
                
                tender = {
                    "ref": ref,
                    "source": org_name,
                    "url": href,
                    "title": title,
                    "short_title": title[:50],
                    "description": title,
                    "client": org_name,
                    "category": category or "Unknown",
                    "closing_date": closing_date,
                    "scraped_date": datetime.now().isoformat()
                }
                
                # Classify
                classification = classify_tender(tender)
                tender["category"] = classification["category"]
                tender["reason"] = classification.get("reason", "")
                
                tenders.append(tender)
                count += 1
                print(f"   ✓ Tender {count}: {ref} - {title[:60]}")
                
            except Exception as e:
                continue
        
        print(f"   ✅ {org_name}: {len(tenders)} tenders found")
        return tenders
        
    except Exception as e:
        print(f"   ❌ {org_name} eTenders scraper error: {e}")
        traceback.print_exc()
        return []
    
    finally:
        if driver:
            driver.quit()


def scrape_eskom():
    """Scrape Eskom tenders from eTenders portal"""
    return scrape_etenders_for_organization("Eskom", "167", max_tenders=30)


def scrape_umgeni_water():
    """Scrape Umgeni Water tenders from eTenders portal"""
    return scrape_etenders_for_organization("Umgeni Water", "683", max_tenders=20)


def scrape_sanral():
    """Scrape SANRAL tenders from eTenders portal"""
    return scrape_etenders_for_organization("SANRAL", "618", max_tenders=20)


def scrape_transnet():
    """Scrape Transnet tenders from eTenders portal"""
    return scrape_etenders_for_organization("Transnet", "667", max_tenders=20)


if __name__ == "__main__":
    # Test
    eskom_tenders = scrape_eskom()
    print(f"\nEskom tenders: {len(eskom_tenders)}")
    for t in eskom_tenders[:3]:
        print(f"  - {t['ref']}: {t['title'][:60]}...")
