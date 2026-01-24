import re
from keyword_rules import SYSTEM_KEYWORDS, ACTION_KEYWORDS

text = "boiler maintenance"

def has_any(text, keywords):
    for kw in keywords:
        if kw in text:
            return kw
    return None

sys_match = has_any(text, SYSTEM_KEYWORDS)
act_match = has_any(text, ACTION_KEYWORDS)

print(f"Text: '{text}'")
print(f"System Match: {sys_match}")
print(f"Action Match: {act_match}")
print(f"Result: {bool(sys_match and act_match)}")
