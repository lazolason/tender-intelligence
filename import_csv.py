# ==========================================================
# CSV TENDER IMPORTER WITH AI SCORING
# Import tenders from CSV file with automatic scoring
# ==========================================================

import csv
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.excel_writer import ExcelWriter
from utils.folder_tools import create_tender_folder
from classify_engine import classify_tender
from scoring_engine import score_tender

# Load config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

EXCEL_PATH = CONFIG["paths"]["tender_log_excel"]
ACTIVE_TENDERS_DIR = CONFIG["paths"]["active_tenders"]
SHEET_NAME = CONFIG["excel"]["tender_log_sheet"]


def import_from_csv(csv_file: str) -> tuple:
    """
    Import tenders from CSV file
    Expected columns: ref, title, description, client, closing_date, source
    Returns (added_count, skipped_count, results_list)
    """
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return 0, 0, []
    
    excel_writer = ExcelWriter(EXCEL_PATH, SHEET_NAME)
    
    added = 0
    skipped = 0
    results = []
    
    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            ref = row.get("ref", "NA").strip()
            title = row.get("title", "").strip()
            description = row.get("description", title).strip()
            client = row.get("client", "").strip()
            closing_date = row.get("closing_date", "").strip()
            source = row.get("source", "CSV Import").strip()
            
            if not title:
                skipped += 1
                continue
            
            tender_data = {
                "ref": ref,
                "title": title,
                "description": description,
                "client": client,
                "closing_date": closing_date,
                "source": source
            }
            
            was_added, scores, classification = excel_writer.add_tender_with_scoring(tender_data)
            
            if was_added:
                added += 1
                
                # Create folder
                folder_path = create_tender_folder(
                    base_dir=ACTIVE_TENDERS_DIR,
                    ref=ref,
                    client=client,
                    short_title=classification["short_title"]
                )
                
                results.append({
                    "ref": ref,
                    "title": title,
                    "category": classification["category"],
                    "priority": scores["priority"],
                    "composite_score": scores["composite_score"],
                    "status": "Added"
                })
                
                print(f"  [{scores['priority']}] ✅ {ref}: {title[:50]}... → {classification['category']} (Score: {scores['composite_score']})")
            else:
                skipped += 1
                results.append({
                    "ref": ref,
                    "title": title,
                    "status": "Skipped (duplicate)"
                })
                print(f"  ⏭️ Skipped (duplicate): {ref}")
    
    return added, skipped, results


# ==========================================================
# MAIN
# ==========================================================
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python import_csv.py <csv_file>")
        print("\nExpected CSV columns:")
        print("  ref, title, description, client, closing_date, source")
        print("\nExample CSV:")
        print('  ref,title,description,client,closing_date,source')
        print('  T001,"Cooling tower chemicals","Supply of chemicals for cooling systems",Eskom,2025-12-15,Manual')
        sys.exit(1)
    
    csv_file = sys.argv[1]
    print(f"\n�� Importing tenders from: {csv_file}")
    print("=" * 50)
    
    added, skipped, results = import_from_csv(csv_file)
    
    print("=" * 50)
    print(f"\n📊 IMPORT SUMMARY:")
    print(f"   Added:   {added}")
    print(f"   Skipped: {skipped}")
    
    # Summary by priority
    high = sum(1 for r in results if r.get("priority") == "HIGH")
    medium = sum(1 for r in results if r.get("priority") == "MEDIUM")
    low = sum(1 for r in results if r.get("priority") == "LOW")
    
    if high + medium + low > 0:
        print(f"\n📈 SCORING BREAKDOWN:")
        print(f"   🔥 HIGH Priority:   {high}")
        print(f"   ✅ MEDIUM Priority: {medium}")
        print(f"   📝 LOW Priority:    {low}")
    
    print(f"\n📁 Excel: {EXCEL_PATH}")
