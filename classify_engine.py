# ==========================================================
# CLASSIFICATION ENGINE V3.0
# MEXEL ENERGY SUSTAIN (TES) LOGIC
# ==========================================================

from keyword_rules import (
    STRONG_MATCH_KEYWORDS, 
    WEAK_MATCH_KEYWORDS, 
    CONTEXT_KEYWORDS, 
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
    Only allow override if strong Mexel/TES signals are present.
    """
    has_strong_signal = len(strong_hits) > 0

    for kw in NEGATIVE_KEYWORDS:
        if kw in text:
            if has_strong_signal:
                # Allow through ONLY when strong water treatment signals exist
                # but log that we ignored a negative for transparency
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
    weak_hits = keyword_hits(text, WEAK_MATCH_KEYWORDS)
    context_hits = keyword_hits(text, CONTEXT_KEYWORDS)

    # ------------------------------------------------------
    # EXCLUSION CHECK FIRST - Skip out-of-scope tenders
    # ------------------------------------------------------
    excluded, exclude_reason = should_exclude(text, strong_hits)
    if excluded:
        return {
            "category": "EXCLUDED",
            "reason": exclude_reason,
            "short_title": make_short_title(title)
        }

    # ------------------------------------------------------
    # SCORE-BASED DECISION
    # ------------------------------------------------------
    
    # Logic 1: Strong match (brand names, specific chemicals)
    if strong_hits:
        return {
            "category": "MEXEL",
            "reason": f"Strong match: {', '.join(strong_hits[:3])}",
            "short_title": make_short_title(title),
            "matched_keywords": list(set(strong_hits + weak_hits + context_hits))
        }

    # Logic 2: Context + Weak Match (e.g. "water treatment" + "chemical supply")
    if context_hits and weak_hits:
        return {
            "category": "MEXEL",
            "reason": f"Context ({context_hits[0]}) + Supporting signal ({weak_hits[0]})",
            "short_title": make_short_title(title),
            "matched_keywords": list(set(strong_hits + weak_hits + context_hits))
        }

    # Logic 3: Multiple context hits (e.g. "boiler water treatment plant")
    # If 3 or more context keywords are found, it's worth looking at
    if len(set(context_hits)) >= 3:
        return {
            "category": "MEXEL",
            "reason": f"High context overlap: {', '.join(list(set(context_hits))[:3])}",
            "short_title": make_short_title(title),
            "matched_keywords": list(set(strong_hits + weak_hits + context_hits))
        }

    # No signals → excluded (Mexel-only)
    return {
        "category": "EXCLUDED",
        "reason": "Excluded: no Mexel/TES keyword match",
        "short_title": make_short_title(title),
        "matched_keywords": []
    }