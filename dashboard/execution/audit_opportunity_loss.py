import re
import os

LOG_PATH = "../logs/scraper.log"
# Keywords we think are over-filtering
OVERFILTER_KWS = ["maintenance", "repair", "servicing", "service provider", "inspection", "plant"]

def audit():
    print("--- POTENTIAL OPPORTUNITIES BLOCKED BY OVER-FILTERING ---")
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
            
            found = 0
            for line in lines:
                if "[SKIP]" in line:
                    # Look for the exclusion reason
                    reason_match = re.search(r"Excluded: '(.*?)'", line)
                    if reason_match:
                        excluded_kw = reason_match.group(1).lower()
                        if any(okw in excluded_kw for okw in OVERFILTER_KWS):
                            # This is a tender we might want
                            tender_info = line.split("[SKIP] ")[-1].split(": Excluded")[0]
                            print(f"Blocked by '{excluded_kw}': {tender_info}")
                            found += 1
                
                if found >= 20:
                    break
            
            if found == 0:
                print("No tenders found in the current log matching those over-filter keywords.")
    else:
        print("Log file not found.")

if __name__ == "__main__":
    audit()
