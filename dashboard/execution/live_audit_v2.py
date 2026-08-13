import sys
import os
import requests
import re

# Add project root to path
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from keyword_rules import NEGATIVE_KEYWORDS, CONTEXT_KEYWORDS, STRONG_MATCH_KEYWORDS, WEAK_MATCH_KEYWORDS

def clean(text: str) -> str:
    if not text: return ""
    text = re.sub(r'[^a-zA-Z0-9\s\-/]', ' ', text)
    return text.lower().strip().replace("\n", " ")

def live_audit():
    print("--- LIVE AUDIT: ESKOM TENDERS (RAW SAMPLES) ---\n")
    
    # Direct API hit to Eskom to get fresh samples
    url = "https://tenderbulletin.eskom.co.za/webapi/api/Lookup/GetTender?TENDER_ID="
    try:
        response = requests.get(url, timeout=30)
        data = response.json()
        
        count = 0
        for item in data:
            if item.get("PUBLISH") != "Y": continue
            
            title = (item.get("HEADER_DESC") or item.get("DESCRIPTION") or "").strip()
            desc = (item.get("SCOPE_DETAILS") or item.get("SUMMARY") or "").strip()
            full_text = clean(f"{title} {desc}")
            
            # Logic Audit
            blocked_by = [kw for kw in NEGATIVE_KEYWORDS if kw in full_text]
            context_hits = [kw for kw in CONTEXT_KEYWORDS if kw in full_text]
            mexel_hits = [kw for kw in STRONG_MATCH_KEYWORDS if kw in full_text]
            
            if blocked_by:
                count += 1
                print(f"SAMPLE {count}:")
                print(f"TITLE:   {title[:100]}...")
                print(f"BLOCKED: {blocked_by}")
                print(f"CONTEXT: {context_hits}")
                print(f"MEXEL:   {mexel_hits}")
                print("-" * 50)
            
            if count >= 15: break
            
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    live_audit()
