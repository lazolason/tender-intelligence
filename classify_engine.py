# ==========================================================
# CLASSIFICATION ENGINE
# TES + PHAKATHI + SWITCHGEAR + BOTH LOGIC
# ==========================================================

from keyword_rules import TES_KEYWORDS, PHAKATHI_KEYWORDS, SWITCHGEAR_KEYWORDS
from keyword_rules import TES_OVERRIDE, PHAKATHI_OVERRIDE, BOTH_CATEGORY_TRIGGERS
from keyword_rules import EXCLUDE_KEYWORDS

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
    """Check if tender matches exclusion keywords. Returns (should_exclude, reason)"""
    for kw in EXCLUDE_KEYWORDS:
        if kw in text:
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
    pakati_score = keyword_hits(text, PHAKATHI_KEYWORDS)
    switchgear_score = keyword_hits(text, SWITCHGEAR_KEYWORDS)

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

    for word in PHAKATHI_OVERRIDE:
        if word in text:
            return {
                "category": "Phakathi",
                "reason": f"Phakathi override keyword detected: '{word}'",
                "short_title": make_short_title(title)
            }

    # ------------------------------------------------------
    # BOTH TRIGGERS
    # ------------------------------------------------------
    for phrase in BOTH_CATEGORY_TRIGGERS:
        if phrase in text:
            return {
                "category": "Both",
                "reason": f"BOTH trigger phrase detected: '{phrase}'",
                "short_title": make_short_title(title)
            }

    # ------------------------------------------------------
    # SWITCHGEAR → Always Phakathi
    # ------------------------------------------------------
    if switchgear_score > 0:
        return {
            "category": "Phakathi",
            "reason": f"Switchgear-related tender ({switchgear_score} hits)",
            "short_title": make_short_title(title)
        }

    # ------------------------------------------------------
    # SCORE-BASED DECISION
    # ------------------------------------------------------
    if tes_score > 0 and pakati_score == 0:
        return {
            "category": "TES",
            "reason": f"TES keyword score: {tes_score}",
            "short_title": make_short_title(title)
        }

    if pakati_score > 0 and tes_score == 0:
        return {
            "category": "Phakathi",
            "reason": f"Phakathi keyword score: {pakati_score}",
            "short_title": make_short_title(title)
        }

    # Overlap → BOTH
    if tes_score > 0 and pakati_score > 0:
        return {
            "category": "Both",
            "reason": f"TES score {tes_score}, Phakathi score {pakati_score}",
            "short_title": make_short_title(title)
        }

    # No signals → Unknown (But still usable)
    return {
        "category": "Unknown",
        "reason": "No clear classification signals detected",
        "short_title": make_short_title(title)
    }

# ----------------------------------------------------------
# PLACEHOLDER FOR FUTURE LLM UNDERSTANDING (GPT)
# ----------------------------------------------------------
def llm_enhancement(description: str):
    """
    This function will later connect to GPT to refine classification.
    For now, it's a placeholder for Phase 3A.
    """
    return None
