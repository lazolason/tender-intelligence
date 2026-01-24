import re
import os

LOG_PATH = "../logs/scraper.log"
# Keywords we suspect are over-filtering
OVERFILTER_KWS = ["maintenance", "repair", "servicing", "service provider", "inspection", "plant"]

def audit():
    print("--- SAMPLE OF MISSING OPPORTUNITIES (FULL TITLES) ---\n")
    if not os.path.exists(LOG_PATH):
        print("Log file not found.")
        return

    # To get titles, we need to look at the SCRAPER output before the exclusion
    # The logs currently only show the Ref in the [SKIP] line.
    # Let's try to find the title from previous INFO lines in the log if possible,
    # or just analyze the Ref/Reason.
    
    with open(LOG_PATH, 'r') as f:
        log_content = f.read()
        
    # Find all instances of [SKIP] and extract the reason
    # Example line: [2026-01-23 21:25:11] [INFO] [SKIP] JW 14040 RR: Excluded: 'construction' (out of scope)
    
    exclusion_pattern = r"\[SKIP\] (.*?): Excluded: '(.*?)'"
    matches = re.findall(exclusion_pattern, log_content)
    
    found = 0
    for ref, reason in matches:
        if any(okw in reason.lower() for okw in OVERFILTER_KWS):
            # Try to find the title for this ref in the same log
            # Titles are often logged during the scraping phase: "✓ Tender 1: REF - TITLE"
            title_pattern = rf"✓ Tender \d+: {re.escape(ref)} - (.*)"
            title_match = re.search(title_pattern, log_content)
            title = title_match.group(1) if title_match else "Title not found in log"
            
            print(f"REF:    {ref}")
            print(f"TITLE:  {title}")
            print(f"REASON: Blocked by keyword '{reason}'")
            print("-" * 50)
            found += 1
            
        if found >= 15:
            break

    if found == 0:
        print("No opportunities with titles found in this log.")

if __name__ == "__main__":
    audit()
