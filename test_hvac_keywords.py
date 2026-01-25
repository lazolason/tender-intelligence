import sys
import os

# Ensure we can import classify_engine
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_engine import classify_tender
from keyword_rules import SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS

# Test cases
test_cases = [
    # Should be MEXEL - Data center cooling
    ("CRAC Unit Water Treatment", "Supply of water treatment chemicals for CRAC unit cooling system at data center facility", "MEXEL"),
    ("Data Center PUE Optimization", "PUE optimization through condenser treatment for data center precision cooling", "MEXEL"),
    ("Computer Room Cooling Chemicals", "Precision cooling water chemistry for computer room CRAH units", "MEXEL"),
    ("Server Room Efficiency", "Data centre cooling water treatment and thermal efficiency improvement", "MEXEL"),
    
    # Should be EXCLUDED - General building HVAC
    ("Office HVAC Installation", "Installation of split unit air conditioning for office building", "EXCLUDED"),
    ("Building Air Conditioning", "Maintenance of building air conditioning and ventilation systems", "EXCLUDED"),
    ("Split Unit Maintenance", "Repair and servicing of office split unit HVAC systems", "EXCLUDED"),
    ("General Ventilation", "Building ventilation system upgrade for commercial offices", "EXCLUDED"),
]

print("=" * 80)
print("HVAC KEYWORD REFINEMENT TEST (V4.0 Engine)")
print("=" * 80)
print()

passed = 0
for title, description, expected in test_cases:
    result = classify_tender(title, description)
    cat = result["category"]
    reason = result["reason"]
    
    status_icon = "✅" if cat == expected else "❌"
    if cat == expected:
        passed += 1
    
    print(f"{status_icon} {cat} (Expected: {expected})")
    print(f"   Title: {title}")
    print(f"   Reason: {reason}")
    print()

print("-" * 80)
print(f"Summary: {passed}/{len(test_cases)} tests passed.")
print("=" * 80)
print()

print("KEYWORD SUMMARY")
print("-" * 80)
dc_systems = [kw for kw in SYSTEM_KEYWORDS if any(x in kw for x in ['crac', 'data', 'computer', 'server', 'precision'])]
print(f"Data Center System Keywords: {dc_systems}")
dc_actions = [kw for kw in ACTION_KEYWORDS if any(x in kw for x in ['pue', 'power usage', 'thermal'])]
print(f"Data Center Action Keywords: {dc_actions}")
hvac_neg = [kw for kw in NEGATIVE_KEYWORDS if any(x in kw for x in ['hvac', 'air conditioning', 'split', 'ventilation'])]
print(f"Building HVAC Exclusions: {hvac_neg}")
print()
