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
        chrome_options.add_argument('--headless')
        chrome_options.add_argument('--no-sandbox')
        chrome_options.add_argument('--disable-dev-shm-usage')
        chrome_options.add_argument('--disable-gpu')
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
        wait = WebDriverWait(driver, 15)
        
        # Click "Currently Advertised" tab
        try:
            active_tab = wait.until(EC.element_to_be_clickable((By.ID, "btnActive")))
            active_tab.click()
            time.sleep(2)
        except:
            pass
        
        # Toggle advanced search
        try:
            show_hide = wait.until(EC.element_to_be_clickable((By.ID, "show_hide")))
            show_hide.click()
            time.sleep(1)
        except:
            pass
        
        # Select organization from dropdown
        try:
            # Use JavaScript to set the value since it might be a Chosen dropdown
            driver.execute_script(f"document.getElementById('departments').value = '{org_id}';")
            time.sleep(0.5)
            
            # Click filter button
            filter_btn = wait.until(EC.element_to_be_clickable((By.ID, "btnFilter")))
            filter_btn.click()
            time.sleep(4)  # Wait for DataTables to reload
        except Exception as e:
            print(f"   ⚠️ Could not filter by organization: {e}")
        
        # Wait for table to load
        wait.until(EC.presence_of_element_located((By.ID, "tendeList")))
        time.sleep(2)
        
        # Find tender rows in the DataTable
        tender_rows = driver.find_elements(By.CSS_SELECTOR, "#tendeList tbody tr")
        
        count = 0
        for row in tender_rows[:max_tenders]:
            try:
                # Skip if it's a "no data" row
                if "dataTables_empty" in row.get_attribute("class"):
                    continue
                
                cells = row.find_elements(By.TAG_NAME, "td")
                if len(cells) < 6:
                    continue
                
                # Extract data from columns
                # Column 1 (index 1): Category
                # Column 2 (index 2): Title/Description  
                # Column 4 (index 4): Advertised date
                # Column 5 (index 5): Closing date
                
                category = cells[1].text.strip() if len(cells) > 1 else ""
                title = cells[2].text.strip() if len(cells) > 2 else ""
                advertised = cells[4].text.strip() if len(cells) > 4 else ""
                closing_date = cells[5].text.strip() if len(cells) > 5 else ""
                
                if not title:
                    continue
                
                # Try to find link in the row
                try:
                    link_elem = cells[2].find_element(By.TAG_NAME, "a")
                    href = link_elem.get_attribute("href")
                except:
                    href = f"https://www.etenders.gov.za/Home/opportunities?search={title[:30]}"
                
                # Try to expand row to get reference number
                ref = ""
                try:
                    expand_btn = cells[0].find_element(By.CSS_SELECTOR, "img, i")
                    expand_btn.click()
                    time.sleep(0.5)
                    
                    # Look for reference in child row
                    child_row = driver.find_element(By.XPATH, f"//tr[contains(@class, 'child')]")
                    ref_text = child_row.text
                    # Extract reference number pattern (e.g., E2253GXGPLET)
                    import re
                    ref_match = re.search(r'[A-Z0-9]{10,}', ref_text)
                    if ref_match:
                        ref = ref_match.group(0)
                    
                    # Click again to collapse
                    expand_btn.click()
                    time.sleep(0.3)
                except:
                    pass
                
                if not ref:
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
