import sqlite3
import sys
import os
import logging
from datetime import datetime

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_engine import classify_tender
from scoring_engine import score_tender
from utils.db_writer import DatabaseWriter

# Configurations
DB_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "tenders.db")

def reclassify_database():
    print("🚀 STARTING DATABASE RE-CLASSIFICATION")
    print("========================================")
    
    if not os.path.exists(DB_PATH):
        print(f"❌ Database not found at {DB_PATH}")
        return

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cursor = conn.cursor()
    
    # Fetch all tenders (focus on EXCLUDED first, but good to check all given the rule changes)
    cursor.execute("SELECT * FROM tenders")
    tenders = cursor.fetchall()
    print(f"📦 Loaded {len(tenders)} tenders from database")
    
    updated_count = 0
    recovered_count = 0
    
    for row in tenders:
        tender_data = dict(row)
        ref = tender_data['ref']
        old_category = tender_data['category']
        
        # Re-classify
        classification = classify_tender(tender_data['title'], tender_data['description'])
        new_category = classification['category']
        new_reason = classification['reason']
        
        # Re-score
        scores = score_tender(
            title=tender_data['title'],
            description=tender_data['description'],
            client=tender_data['client'],
            closing_date=tender_data['closing_date'],
            category=new_category
        )
        
        old_priority = tender_data.get('priority')
        old_composite = tender_data.get('composite_score')
        old_reason = tender_data.get('classification_reason')
        old_keywords = tender_data.get('matched_keywords') or ""
        new_keywords = ", ".join(classification.get("matched_keywords", []))

        # Check for meaningful change in category or derived scoring/classification fields.
        if (
            new_category != old_category
            or scores['priority'] != old_priority
            or float(scores['composite_score']) != float(old_composite or 0)
            or new_reason != old_reason
            or new_keywords != old_keywords
        ):
            
            # Prepare Update
            cursor.execute("""
                UPDATE tenders 
                SET category = ?, 
                    classification_reason = ?,
                    fit_score = ?,
                    industry_score = ?,
                    mexel_suitability = ?,
                    composite_score = ?,
                    priority = ?,
                    recommendation = ?,
                    matched_keywords = ?
                WHERE ref = ?
            """, (
                new_category,
                new_reason,
                scores['fit_score'],
                scores['industry_score'],
                scores['mexel_suitability'],
                scores['composite_score'],
                scores['priority'],
                scores['recommendation'],
                    new_keywords,
                    ref
            ))
            
            updated_count += 1
            if old_category == 'EXCLUDED' and new_category == 'MEXEL':
                recovered_count += 1
                print(f"♻️  RECOVERED: {ref} ({old_category} -> {new_category}) | {tender_data['title'][:60]}...")
            elif new_category == 'MEXEL':
                 print(f"⚡ UPDATED: {ref} (Score: {scores['composite_score']}) | {tender_data['title'][:60]}...")
                 
    conn.commit()
    conn.close()
    
    print("\n" + "=" * 40)
    print(f"🎉 RE-CLASSIFICATION COMPLETE")
    print(f"   Total Updated: {updated_count}")
    print(f"   Recovered from Excluded: {recovered_count}")
    print("=" * 40)

if __name__ == "__main__":
    reclassify_database()
