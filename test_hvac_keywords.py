#!/usr/bin/env python3
"""
Test script to validate the HVAC keyword refinement.
Demonstrates that data center cooling is now INCLUDED while general building HVAC is EXCLUDED.
"""

import sys
sys.path.insert(0, '/Users/lazolasonqishe/Documents/tender-intelligence')

from keyword_rules import STRONG_MATCH_KEYWORDS, SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS

def has_any(text, keywords):
    """Check if any keyword appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

def classify_tender(title, description):
    """Classify a tender using the keyword rules."""
    full_text = f"{title} {description}".lower()
    
    # Check for negative keywords first
    neg_matches = [kw for kw in NEGATIVE_KEYWORDS if kw.lower() in full_text]
    if neg_matches:
        return "EXCLUDED", f"Negative keywords: {neg_matches}"
    
    # Check for strong match
    strong_matches = [kw for kw in STRONG_MATCH_KEYWORDS if kw.lower() in full_text]
    if strong_matches:
        return "INCLUDED", f"Strong match: {strong_matches}"
    
    # Check for system + action pairing
    system_matches = [kw for kw in SYSTEM_KEYWORDS if kw.lower() in full_text]
    action_matches = [kw for kw in ACTION_KEYWORDS if kw.lower() in full_text]
    
    if system_matches and action_matches:
        return "INCLUDED", f"System: {system_matches}, Action: {action_matches}"
    
    return "EXCLUDED", "No matching criteria"

# Test cases
test_cases = [
    # Should be INCLUDED - Data center cooling
    ("CRAC Unit Water Treatment", "Supply of water treatment chemicals for CRAC unit cooling system at data center facility"),
    ("Data Center PUE Optimization", "PUE optimization through condenser treatment for data center precision cooling"),
    ("Computer Room Cooling Chemicals", "Precision cooling water chemistry for computer room CRAH units"),
    ("Server Room Efficiency", "Data centre cooling water treatment and thermal efficiency improvement"),
    
    # Should be EXCLUDED - General building HVAC
    ("Office HVAC Installation", "Installation of split unit air conditioning for office building"),
    ("Building Air Conditioning", "Maintenance of building air conditioning and ventilation systems"),
    ("Split Unit Maintenance", "Repair and servicing of office split unit HVAC systems"),
    ("General Ventilation", "Building ventilation system upgrade for commercial offices"),
]

print("=" * 80)
print("HVAC KEYWORD REFINEMENT TEST")
print("=" * 80)
print()

for title, description in test_cases:
    result, reason = classify_tender(title, description)
    status_icon = "✅" if result == "INCLUDED" else "❌"
    
    print(f"{status_icon} {result}")
    print(f"   Title: {title}")
    print(f"   Reason: {reason}")
    print()

print("=" * 80)
print("KEYWORD SUMMARY")
print("=" * 80)
print()
print(f"Data Center System Keywords: {[kw for kw in SYSTEM_KEYWORDS if 'crac' in kw or 'data' in kw or 'computer' in kw or 'server' in kw or 'precision' in kw]}")
print()
print(f"Data Center Action Keywords: {[kw for kw in ACTION_KEYWORDS if 'pue' in kw or 'power usage' in kw or 'thermal' in kw]}")
print()
print(f"Building HVAC Exclusions: {[kw for kw in NEGATIVE_KEYWORDS if 'hvac' in kw or 'air conditioning' in kw or 'split' in kw or 'ventilation' in kw]}")
print()
