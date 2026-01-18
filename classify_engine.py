# ==========================================================
# CLASSIFICATION ENGINE
# TES-ONLY LOGIC
# ==========================================================

from keyword_rules import TES_KEYWORDS, TES_OVERRIDE, EXCLUDE_KEYWORDS

import re

# ----------------------------------------------------------
# CLEAN TEXT FOR MATCHING
# ----------------------------------------------------------
def clean(text: str) -> str:
    if not text:
        return ""
    return text.lower().strip().replace("\n", " ")

# ----------------------------------------------------------
# CHECK FOR KEYWORD MATCHES
# ----------------------------------------------------------
def keyword_hits(text: str, keywords: list) -> int:
    return sum(1 for kw in keywords if kw in text)

# ----------------------------------------------------------
# CHECK IF TENDER SHOULD BE EXCLUDED
# ----------------------------------------------------------
def should_exclude(text: str) -> tuple:
    """
    Check if tender matches exclusion keywords. Returns (should_exclude, reason).
    Only allow override if STRONG TES signals are present.
    """
    from keyword_rules import TES_STRONG_SIGNALS

    # Check for strong override signals (water treatment)
    has_strong_signal = any(kw in text for kw in TES_STRONG_SIGNALS)

    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
            if has_strong_signal:
                # Allow through ONLY when strong water treatment signals exist
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

    # ------------------------------------------------------
    # EXCLUSION CHECK FIRST - Skip out-of-scope tenders
    # ------------------------------------------------------
    excluded, exclude_reason = should_exclude(text)
    if excluded:
        return {
            "category": "EXCLUDED",
            "reason": exclude_reason,
            "short_title": make_short_title(title)
        }

    tes_score = keyword_hits(text, TES_KEYWORDS)

    # ------------------------------------------------------
    # OVERRIDE RULES
    # ------------------------------------------------------
    for word in TES_OVERRIDE:
        if word in text:
            return {
                "category": "TES",
                "reason": f"TES override keyword detected: '{word}'",
                "short_title": make_short_title(title)
            }

    # ------------------------------------------------------
    # SCORE-BASED DECISION
    # ------------------------------------------------------
    if tes_score > 0:
        return {
            "category": "TES",
            "reason": f"TES keyword score: {tes_score}",
            "short_title": make_short_title(title)
        }

    # No signals → Unknown (But still usable)
    return {
        "category": "Unknown",
        "reason": "No clear classification signals detected",
        "short_title": make_short_title(title)
    }
