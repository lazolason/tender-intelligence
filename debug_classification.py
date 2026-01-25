import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from classify_engine import classify_tender, keyword_hits, should_exclude, clean
from keyword_rules import SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS

# Target Tender Data (from logs)
title = "THE MEDUPI POWER STATION FLUE GAS DESULPHURIZATION (FGD) RETROFIT ENGINEER, PROCURE, CONSTRUCT (EPC)"
description = "THE MEDUPI POWER STATION FLUE GAS DESULPHURIZATION (FGD) RETROFIT ENGINEER, PROCURE, CONSTRUCT (EPC) PROJECT FOR AN ESTIMATED CONTRACT PERIOD OF EIGHT (8) YEARS."

print("🔍 DEBUGGING CLASSIFICATION")
print(f"Title: {title}")
print("-" * 50)

# 1. Clean Text
text = clean(f"{title} {description}")
print(f"Cleaned Text: {text}")

# 2. Keywords Checks
print("\n--- KEYWORD HITS ---")
systems = keyword_hits(text, SYSTEM_KEYWORDS)
actions = keyword_hits(text, ACTION_KEYWORDS)
negatives = keyword_hits(text, NEGATIVE_KEYWORDS)

print(f"Systems: {systems}")
print(f"Actions: {actions}")
print(f"Negatives: {negatives}")

# 3. Exclusion Check
excluded, reason = should_exclude(text, [])
print(f"\nExcluded? {excluded}")
if excluded:
    print(f"Reason: {reason}")

# 4. Final Classification
result = classify_tender(title, description)
print("\n--- RESULT ---")
print(result)
