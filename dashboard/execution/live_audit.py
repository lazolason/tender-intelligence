import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from scrapers.eskom_direct import _scrape_eskom_tenders_api
from classify_engine import classify_tender, clean, keyword_hits
from keyword_rules import NEGATIVE_KEYWORDS

def live_audit():
    print("--- LIVE AUDIT: ESKOM TENDERS THAT WOULD BE EXCLUDED ---\n")
    try:
        tenders = _scrape_eskom_tenders_api(max_tenders=50)
        
        excluded_count = 0
        for t in tenders:
            text = clean(f"{t['title']} {t['description']}")
            
            # Manually check for negative keywords
            blocked_by = [kw for kw in NEGATIVE_KEYWORDS if kw in text]
            
            if blocked_by:
                excluded_count += 1
                if excluded_count <= 15:
                    print(f"REF:    {t['ref']}")
                    print(f"TITLE:  {t['title']}")
                    print(f"BLOCKED BY: {blocked_by}")
                    print("-" * 50)
        
        print(f"\nTotal Eskom tenders audited: {len(tenders)}")
        print(f"Tenders that would be excluded: {excluded_count}")
        
    except Exception as e:
        print(f"Audit failed: {e}")

if __name__ == "__main__":
    live_audit()
