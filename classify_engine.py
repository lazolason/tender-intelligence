# ==========================================================
# CLASSIFICATION ENGINE V4.0
# MEXEL ENERGY SUSTAIN LOGIC (PHASE 2)
# ==========================================================

from keyword_rules import (
    STRONG_MATCH_KEYWORDS, 
    SYSTEM_KEYWORDS, 
    ACTION_KEYWORDS, 
    NEGATIVE_KEYWORDS
)

import re

# ----------------------------------------------------------
# CLEAN TEXT FOR MATCHING
# ----------------------------------------------------------
def clean(text: str) -> str:
    if not text:
        return ""
    # Remove extra whitespace and special characters that might break matching
    text = re.sub(r'[^a-zA-Z0-9\s\-/]', ' ', text)
    return text.lower().strip().replace("\n", " ")

# ----------------------------------------------------------
# CHECK FOR KEYWORD MATCHES
# ----------------------------------------------------------
def keyword_hits(text: str, keywords: list) -> list:
    """Returns a list of matched keywords for debugging/reasoning"""
    return [kw for kw in keywords if kw in text]

# ----------------------------------------------------------
# CHECK IF TENDER SHOULD BE EXCLUDED
# ----------------------------------------------------------
def should_exclude(text: str, strong_hits: list) -> tuple:
    """
    Check if tender matches negative keywords. Returns (should_exclude, reason).
    Only allow override if strong Mexel signals (Profile A) are present.
    """
    has_strong_signal = len(strong_hits) > 0

    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            if has_strong_signal:
                # PROFILE A (Strong Match) overrides exclusions
                return False, None
            return True, f"Excluded: '{kw}' (out of scope)"
    return False, None

# ----------------------------------------------------------
# SIMPLE SHORT TITLE MAKER
# ----------------------------------------------------------
def make_short_title(original_title: str) -> str:
    title = clean(original_title)
    # Remove tender fluff words
    remove_words = ["tender for", "appointment of", "for the", "supply and delivery of",
                    "supply & delivery", "supply of", "provision of", "services",
                    "service", "works", "project", "contract", "repairs", "maintenance"]

    for w in remove_words:
        title = title.replace(w, "")

    # Keep first 4 meaningful words
    parts = [word.capitalize() for word in re.findall(r"[A-Za-z0-9]+", title)]
    return "_".join(parts[:4]) if parts else "General_Scope"

# ----------------------------------------------------------
# MAIN CLASSIFICATION FUNCTION
# ----------------------------------------------------------
def classify_tender(title: str, description: str) -> dict:
    text = clean(f"{title} {description}")

    # Count hits in all categories
    strong_hits = keyword_hits(text, STRONG_MATCH_KEYWORDS)
    system_hits = keyword_hits(text, SYSTEM_KEYWORDS)
    action_hits = keyword_hits(text, ACTION_KEYWORDS)

    # 1. EXCLUSION CHECK FIRST
    excluded, exclude_reason = should_exclude(text, strong_hits)
    if excluded:
        return {
            "category": "EXCLUDED",
            "reason": exclude_reason,
            "short_title": make_short_title(title)
        }

    # 2. PROFILE A: THE PRODUCT (Automatic Match)
    if strong_hits:
        return {
            "category": "MEXEL",
            "reason": f"Strong Match (Profile A): {', '.join(strong_hits[:3])}",
            "short_title": make_short_title(title),
            "matched_keywords": list(set(strong_hits + system_hits + action_hits))
        }

    # 3. PROFILE B: SYSTEM + ACTION (Must be paired)
    if system_hits and action_hits:
        return {
            "category": "MEXEL",
            "reason": f"Competence Match (Profile B): {system_hits[0]} + {action_hits[0]}",
            "short_title": make_short_title(title),
            "matched_keywords": list(set(strong_hits + system_hits + action_hits))
        }

    # No signals → excluded (Mexel-only)
    return {
        "category": "EXCLUDED",
        "reason": "Excluded: no Profile A or Profile B match",
        "short_title": make_short_title(title),
        "matched_keywords": []
    }
