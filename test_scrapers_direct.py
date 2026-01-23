import sys
import os

# Add relevant paths
PROJECT_DIR = "/Users/lazolasonqishe/Documents/tender-intelligence"
sys.path.insert(0, PROJECT_DIR)

from scrapers.sadc import scrape_all_sadc
from scrapers.water_boards import scrape_all_water_boards

print("--- Testing Water Boards ---")
wb_tenders = scrape_all_water_boards()
print(f"Found {len(wb_tenders)} Water Board tenders")

print("\n--- Testing SADC ---")
sadc_tenders = scrape_all_sadc()
print(f"Found {len(sadc_tenders)} SADC tenders")

if wb_tenders:
    print("\nSample Water Board tender:")
    print(wb_tenders[0])

if sadc_tenders:
    print("\nSample SADC tender:")
    print(sadc_tenders[0])
