# ==========================================================
# CSV TENDER IMPORTER WITH SCORING
# Import tenders from CSV into SQLite with automatic scoring
# ==========================================================

import csv
import os
import sys
import yaml

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.db_writer import DatabaseWriter
from utils.folder_tools import create_tender_folder
from utils.pipeline_validation import validate_tender_batch

# Load config
config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.yaml")
with open(config_path, "r") as f:
    CONFIG = yaml.safe_load(f)

DB_PATH = os.getenv("DB_PATH", os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tenders.db"))
ACTIVE_TENDERS_DIR = CONFIG["paths"]["active_tenders"]


def import_from_csv(csv_file: str) -> tuple:
    """
    Import tenders from CSV file
    Expected columns: ref, title, description, client, closing_date, source
    Returns (added_count, skipped_count, results_list)
    """
    
    if not os.path.exists(csv_file):
        print(f"❌ File not found: {csv_file}")
        return 0, 0, []
    
    db_writer = DatabaseWriter(DB_PATH)
    
    added = 0
    skipped = 0
    results = []
    candidates = []

    with open(csv_file, "r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            title = (row.get("title") or "").strip()
            candidates.append({
                "ref": (row.get("ref") or "").strip(),
                "title": title,
                "description": (row.get("description") or title).strip(),
                "client": (row.get("client") or "").strip(),
                "closing_date": (row.get("closing_date") or "").strip(),
                "source": (row.get("source") or "CSV Import").strip(),
            })

    validation = validate_tender_batch(
        candidates,
        on_invalid=lambda message: print(f"  ❌ {message}"),
    )
    skipped += validation.invalid_count

    for tender_data in validation.valid_tenders:
        ref = tender_data["ref"]
        title = tender_data["title"]
        client = tender_data["client"]
        action, scores, classification = db_writer.upsert_tender_with_scoring(tender_data)

        if action == "inserted":
            added += 1
            create_tender_folder(
                base_dir=ACTIVE_TENDERS_DIR,
                ref=ref,
                client=client,
                short_title=classification["short_title"],
            )
            results.append({
                "ref": ref,
                "title": title,
                "category": classification["category"],
                "priority": scores["priority"],
                "composite_score": scores["composite_score"],
                "status": "Added",
            })
            print(
                f"  [{scores['priority']}] ✅ {ref}: {title[:50]}... → "
                f"{classification['category']} (Score: {scores['composite_score']})"
            )
        elif action == "updated":
            results.append({
                "ref": ref,
                "title": title,
                "priority": scores["priority"],
                "status": "Updated",
            })
            print(f"  🔄 Updated: {ref}")
        else:
            skipped += 1
            results.append({
                "ref": ref,
                "title": title,
                "status": "Unchanged",
            })
            print(f"  ⏭️ Unchanged: {ref}")
    
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
    print(f"\nImporting tenders from: {csv_file}")
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
    
    print(f"\n🗄️ Database: {DB_PATH}")
