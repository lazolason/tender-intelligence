import sys
import os
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, PROJECT_ROOT)

from classify_engine import classify_tender

test_cases = [
    ("MPHEN11110GXAWARD", "Award of Operation and management of the Sewage treatment plant at Hendrina Power Station"),
    ("MPKUS11014GXR1", "The Provision of Operating and Commissioning Support Resources for Kusile Power Station for a period"),
    ("E2138GXMWP", "Request For Information (RFI) for South African Hydroelectric Power Station Development.")
]

print("--- VERIFYING PHASE 2 CLASSIFICATION ---")
for ref, title in test_cases:
    result = classify_tender(title, title)
    print(f"REF: {ref}")
    print(f"TITLE: {title[:60]}...")
    print(f"RESULT: {result['category']} | REASON: {result['reason']}")
    print("-" * 40)
