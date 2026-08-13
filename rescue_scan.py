import sys
import os
import json
from datetime import datetime

# Setup path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from scrapers.eskom_direct import scrape_eskom_tenders
from tenderscan import process_tenders, save_outputs
from utils.pipeline_validation import validate_tender_batch

print("🚀 STARTING RESCUE SCAN FOR MEXEL TENDERS")
print("=========================================")

# Run API scraper with broad range (API filters are looser, so fetching more helps)
try:
    print("\n🔍 Running Eskom API scan (Deep Recovery)...")
    tenders = scrape_eskom_tenders(max_tenders=5000, use_selenium_fallback=False)
    print(f"✅ Found {len(tenders)} tenders")
    
    # Filter for our specific targets to verify
    targets = ["Matla", "Medupi", "Grootvlei", "Cooling", "Water"]
    hits = [t for t in tenders if any(x in str(t).replace("'", "") for x in targets)]
    print(f"🎯 Targeted hits: {len(hits)}")
    for h in hits[:5]:
        print(f"   - {h['ref']}: {h['title'][:60]}...")

    # Validate, Process and Save
    print("\n💾 Validating, processing and saving...")
    validation = validate_tender_batch(
        tenders,
        on_invalid=lambda message: print(f"⚠️ {message}"),
    )
    print(
        f"✅ Validation: {validation.valid_count} valid / "
        f"{validation.invalid_count} invalid"
    )
    added, new_items = process_tenders(validation.valid_tenders)
    save_outputs(new_items, validation_report_text=validation.report_text)
    print(f"✅ Saved {len(new_items)} new items to dashboard")

except Exception as e:
    print(f"❌ Rescue scan failed: {e}")
    import traceback
    traceback.print_exc()
