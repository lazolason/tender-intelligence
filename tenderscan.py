# ==========================================================
# TENDER AUTOMATION ENGINE — MAIN RUNNER
# Scrapes all sources, classifies, SCORES, logs to Excel, creates folders
# ==========================================================

import json
import yaml
from datetime import datetime
import sys
import os

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# Import scrapers
from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import scrape_all_soes

# Import utils
from utils.excel_writer import ExcelWriter
from utils.folder_tools import create_tender_folder, folder_creation_log
from utils.logging_tools import write_log, log_start, log_end, log_error, rotate_log_if_needed

# Import scoring engine
from scoring_engine import score_tender

# ----------------------------------------------------------
# LOAD CONFIG
# ----------------------------------------------------------
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

# Paths
EXCEL_PATH = CONFIG["paths"]["tender_log_excel"]
ACTIVE_TENDERS_DIR = CONFIG["paths"]["active_tenders"]
OUTPUT_DIR = CONFIG["paths"]["output_dir"]
LOG_FILE = CONFIG["paths"]["log_file"]
SHEET_NAME = CONFIG["excel"]["tender_log_sheet"]

# Selenium scraper toggle (set to True to enable)
ENABLE_SELENIUM = CONFIG.get("scrapers", {}).get("enable_selenium", True)

# Ensure directories exist
os.makedirs(OUTPUT_DIR, exist_ok=True)
os.makedirs(ACTIVE_TENDERS_DIR, exist_ok=True)
os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)

# ----------------------------------------------------------
# INITIALISE EXCEL WRITER
# ----------------------------------------------------------
excel_writer = ExcelWriter(EXCEL_PATH, SHEET_NAME)

# ----------------------------------------------------------
# RUN ALL SCRAPERS
# ----------------------------------------------------------
def run_all_scrapers():
    all_tenders = []
    
    # Municipalities
    write_log(LOG_FILE, "=== Scraping Municipalities ===")
    try:
        muni_tenders = scrape_all_municipalities()
        all_tenders.extend(muni_tenders)
        write_log(LOG_FILE, f"Municipalities: {len(muni_tenders)} tenders found")
    except Exception as e:
        log_error(LOG_FILE, f"Municipality scraper failed: {e}")
    
    # SOEs
    write_log(LOG_FILE, "=== Scraping SOEs ===")
    try:
        soe_tenders = scrape_all_soes()
        all_tenders.extend(soe_tenders)
        write_log(LOG_FILE, f"SOEs: {len(soe_tenders)} tenders found")
    except Exception as e:
        log_error(LOG_FILE, f"SOE scraper failed: {e}")
    
    # National Treasury (Selenium) - Optional
    if ENABLE_SELENIUM:
        write_log(LOG_FILE, "=== Scraping National Treasury (Selenium) ===")
        try:
            from scrapers.national_treasury_selenium import scrape_national_treasury
            nt_tenders = scrape_national_treasury()
            all_tenders.extend(nt_tenders)
            write_log(LOG_FILE, f"National Treasury: {len(nt_tenders)} tenders found")
        except ImportError:
            log_error(LOG_FILE, "Selenium not available - skipping National Treasury")
        except Exception as e:
            log_error(LOG_FILE, f"National Treasury scraper failed: {e}")
    
    return all_tenders

# ----------------------------------------------------------
# PROCESS TENDERS WITH AI SCORING
# ----------------------------------------------------------
def process_tenders(tenders):
    total_added = 0
    new_items = []

    for t in tenders:
        try:
            ref = t.get("ref", "NA")
            title = t.get("title", "")
            description = t.get("description", title)
            client = t.get("client", "")
            category = t.get("category", "Unknown")
            closing_date = t.get("closing_date", "")
            short_title = t.get("short_title", "Tender")
            reason = t.get("reason", "")
            source = t.get("source", "")
            
            tender_name = f"{ref} - {title}" if ref and ref != "NA" else title
            
            # AI SCORING ENGINE
            scores = score_tender(
                title=title,
                description=description,
                client=client,
                closing_date=closing_date,
                category=category
            )
            
            fit_score = scores["fit_score"]
            industry_score = scores["industry_score"]
            risk_score = scores["risk_score"]
            revenue_score = scores["revenue_score"]
            tes_suitability = scores["tes_suitability"]
            phakathi_suitability = scores["phakathi_suitability"]
            composite_score = scores["composite_score"]
            priority = scores["priority"]
            recommendation = scores["recommendation"]
            
            # Add scores to tender dict
            t["scores"] = {
                "fit": fit_score,
                "industry": industry_score,
                "risk": risk_score,
                "revenue": revenue_score,
                "tes": tes_suitability,
                "phakathi": phakathi_suitability,
                "composite": composite_score,
                "priority": priority
            }
            
            # Build notes with scoring info
            enhanced_notes = f"{reason}\n" if reason else ""
            enhanced_notes += f"[AI Score: {composite_score}/10 | Priority: {priority}]"
            enhanced_notes += f"\n{recommendation}"
            
            # Write to Excel
            added = excel_writer.write_tender(
                tender_name=tender_name,
                client=client,
                tender_type=category,
                industry=f"{source} ({scores['industry_matched']})",
                fit_score=fit_score,
                stage="New",
                closing_date=closing_date,
                status="Open",
                next_action="Review" if priority == "LOW" else "Prepare Bid" if priority == "MEDIUM" else "URGENT BID",
                notes=enhanced_notes,
                reference_number=ref,
                composite_score=composite_score,
                priority=priority,
                risk_level=scores["risk_level"],
                revenue_potential=scores["revenue_potential"],
                tes_fit=tes_suitability,
                phakathi_fit=phakathi_suitability
            )

            if added:
                total_added += 1
                new_items.append(t)
    
                # Create tender folder
                folder_path = create_tender_folder(
                    base_dir=ACTIVE_TENDERS_DIR,
                    ref=ref,
                    client=client,
                    short_title=short_title
                )

                write_log(LOG_FILE, f"[{priority}] Added: {tender_name} → {category} (Score: {composite_score})")
    
        except Exception as e:
            log_error(LOG_FILE, f"Error processing tender: {e}")
            continue

    return total_added, new_items

# ----------------------------------------------------------
# SAVE OUTPUT REPORTS
# ----------------------------------------------------------
def save_outputs(new_items):
    # Save JSON
    json_path = os.path.join(OUTPUT_DIR, "new_tenders.json")
    with open(json_path, "w") as jf:
        json.dump(new_items, jf, indent=4)
    
    # Save text summary
    summary_path = os.path.join(OUTPUT_DIR, "summary.txt")
    with open(summary_path, "w") as sf:
        sf.write(f"Tender Scan Summary\n")
        sf.write(f"===================\n")
        sf.write(f"Run date: {datetime.now()}\n")
        sf.write(f"New tenders added: {len(new_items)}\n\n")
        
        # Group by priority
        high_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "HIGH"]
        medium_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM"]
        low_priority = [t for t in new_items if t.get("scores", {}).get("priority") == "LOW"]
        
        sf.write(f"\n🔥 HIGH PRIORITY ({len(high_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in high_priority:
            sf.write(f"  [{t['scores']['composite']}] {t['ref']} | {t['title'][:50]}...\n")
        
        sf.write(f"\n✅ MEDIUM PRIORITY ({len(medium_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in medium_priority:
            sf.write(f"  [{t['scores']['composite']}] {t['ref']} | {t['title'][:50]}...\n")
        
        sf.write(f"\n📝 LOW PRIORITY ({len(low_priority)}):\n")
        sf.write("-" * 40 + "\n")
        for t in low_priority:
            sf.write(f"  [{t['scores']['composite']}] {t['ref']} | {t['title'][:50]}...\n")
        
        # Group by source
        sf.write(f"\n\nBY SOURCE:\n")
        sf.write("=" * 40 + "\n")
        by_source = {}
        for t in new_items:
            src = t.get("source", "Unknown")
            if src not in by_source:
                by_source[src] = []
            by_source[src].append(t)
        
        for source, items in by_source.items():
            sf.write(f"\n{source} ({len(items)}):\n")
            for t in items:
                sf.write(f"  - {t['ref']} | {t['title'][:50]}... | {t['category']}\n")

# ----------------------------------------------------------
# MAIN ENTRY POINT
# ----------------------------------------------------------
if __name__ == "__main__":
    rotate_log_if_needed(LOG_FILE)
    
    write_log(LOG_FILE, "=" * 50)
    write_log(LOG_FILE, "TENDER ENGINE RUN STARTED (WITH AI SCORING)")
    write_log(LOG_FILE, "=" * 50)
    
    # Scrape all sources
    all_tenders = run_all_scrapers()
    
    write_log(LOG_FILE, f"Total tenders scraped: {len(all_tenders)}")
    
    # Process, classify & SCORE
    added_count, new_items = process_tenders(all_tenders)
    
    # Save results
    save_outputs(new_items)
    
    write_log(LOG_FILE, "=" * 50)
    write_log(LOG_FILE, f"TENDER ENGINE COMPLETE - Added: {added_count}")
    write_log(LOG_FILE, "=" * 50)
    
    # Print summary by priority
    high = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "HIGH")
    medium = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "MEDIUM")
    low = sum(1 for t in new_items if t.get("scores", {}).get("priority") == "LOW")
    
    print(f"\n🎉 Tender scan complete!")
    print(f"   Total scraped: {len(all_tenders)}")
    print(f"   New tenders added: {added_count}")
    print(f"\n📊 AI SCORING SUMMARY:")
    print(f"   🔥 HIGH Priority:   {high}")
    print(f"   ✅ MEDIUM Priority: {medium}")
    print(f"   📝 LOW Priority:    {low}")
    print(f"\nCheck output at: {OUTPUT_DIR}")
