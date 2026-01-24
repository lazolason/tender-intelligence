import json
import os

LOG_PATH = "../logs/scraper.log"

def audit():
    print("--- SAMPLE OF EXCLUDED TENDERS (LAST RUN) ---")
    if os.path.exists(LOG_PATH):
        with open(LOG_PATH, 'r') as f:
            lines = f.readlines()
            # Filter for exclusion lines
            exclusions = [l.strip() for l in lines if "[SKIP]" in l]
            
            if not exclusions:
                print("No exclusion logs found.")
                return

            # Take a sample of 15 exclusions
            sample = exclusions[-15:]
            for i, line in enumerate(sample, 1):
                # Clean up the log timestamp and prefix
                clean = line.split("] [INFO] ")[-1] if "] [INFO] " in line else line
                print(f"{i}. {clean}")
    else:
        print(f"Log file not found at {LOG_PATH}")

if __name__ == "__main__":
    audit()
