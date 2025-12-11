#!/usr/bin/env python3
"""
Re-classify existing tenders with updated keyword rules
"""
import json
from classify_engine import classify_tender

INPUT_PATH = "/Users/lazolasonqishe/Documents/MASTER/TENDERS/00_System/04_Automation/output/new_tenders.json"
OUTPUT_PATH = INPUT_PATH  # Overwrite in place

print("Loading existing tenders...")
with open(INPUT_PATH) as f:
    tenders = json.load(f)

print(f"Found {len(tenders)} tenders\n")

excluded_count = 0
reclassified_count = 0
kept_tenders = []

for tender in tenders:
    title = tender.get("title", "")
    description = tender.get("description", "")
    old_category = tender.get("category", "Unknown")
    
    # Re-classify
    classification = classify_tender(title, description)
    new_category = classification["category"]
    
    # Skip excluded tenders
    if new_category == "EXCLUDED":
        excluded_count += 1
        reason = classification.get("reason", "")
        print(f"[EXCLUDE] {tender.get('ref', 'N/A')}: {reason}")
        continue
    
    # Update tender with new classification
    if new_category != old_category:
        reclassified_count += 1
        print(f"[RECLASSIFY] {tender.get('ref', 'N/A')}: {old_category} → {new_category}")
    
    tender["category"] = new_category
    tender["reason"] = classification.get("reason", "")
    tender["short_title"] = classification.get("short_title", tender.get("short_title", ""))
    
    kept_tenders.append(tender)

print(f"\n{'='*60}")
print(f"Results:")
print(f"  Total processed: {len(tenders)}")
print(f"  Excluded: {excluded_count}")
print(f"  Reclassified: {reclassified_count}")
print(f"  Kept: {len(kept_tenders)}")
print(f"{'='*60}\n")

# Save updated tenders
with open(OUTPUT_PATH, "w") as f:
    json.dump(kept_tenders, f, indent=2)

print(f"✅ Updated file saved to: {OUTPUT_PATH}")

# Show new category breakdown
from collections import Counter
categories = Counter(t["category"] for t in kept_tenders)
print(f"\nNew category breakdown:")
for cat, count in categories.most_common():
    print(f"  {cat}: {count}")
