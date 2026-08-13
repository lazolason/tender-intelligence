# ==========================================================
# CLASSIFICATION ENGINE V5.0
# MULTI-COMPANY: MEXEL / PHAKATHI
# ==========================================================

from keyword_rules import (
    STRONG_MATCH_KEYWORDS,
    SYSTEM_KEYWORDS,
    ACTION_KEYWORDS,
    NEGATIVE_KEYWORDS,
    BROAD_SYSTEM_KEYWORDS,
    BROAD_ACTION_KEYWORDS,
    PHAKATHI_KEYWORDS,
)

import re

# ----------------------------------------------------------
# CLEAN TEXT FOR MATCHING
# ----------------------------------------------------------
def clean(text: str) -> str:
    if not text:
        return ""
    text = re.sub(r'[^a-zA-Z0-9\s\-/]', ' ', text)
    text = text.replace("-", " ").replace("/", " ")
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip().replace("\n", " ")

# ----------------------------------------------------------
# CHECK FOR KEYWORD MATCHES
# ----------------------------------------------------------
def keyword_present(text: str, keyword: str) -> bool:
    """Match a normalized keyword without allowing alphanumeric substrings."""
    pattern = rf"(?<![a-z0-9]){re.escape(keyword)}(?![a-z0-9])"
    return re.search(pattern, text) is not None


def keyword_hits(text: str, keywords: list) -> list:
    """Return stable, boundary-aware keyword matches for reasoning."""
    return [kw for kw in keywords if keyword_present(text, kw)]

def build_matched_keywords(
    text: str,
    strong_hits: list,
    system_hits: list,
    action_hits: list,
    phakathi_hits: list | None = None,
) -> list:
    """Build stable matched-keyword output with useful composite aliases."""
    matched = set(strong_hits + system_hits + action_hits)

    if phakathi_hits:
        matched.update(phakathi_hits)

    if "chemical dosing" in text or ("chemical" in matched and "dosing" in matched):
        matched.add("chemical dosing")
    if "boiler" in matched and "water treatment" in matched:
        matched.add("boiler water treatment")
    if "ro system" in matched or "reverse osmosis" in matched:
        matched.add("ro")
    if "cnc machining" in matched or "precision machining" in matched:
        matched.add("machining")
    if "mechanical seal" in matched or "gland packing" in matched:
        matched.add("seal/packing")

    for token in ("industrial", "utility", "plant"):
        if f" {token} " in f" {text} ":
            matched.add(token)

    return list(matched)


def has_specific_profile_b_signal(system_hits: list, action_hits: list) -> bool:
    """
    Profile B should not trigger on broad site + generic action combinations.

    Examples we want to avoid:
    - power station + service
    - tutuka + supply
    - majuba + refurbishment
    """
    broad_systems = {kw for kw in BROAD_SYSTEM_KEYWORDS}
    broad_actions = {kw for kw in BROAD_ACTION_KEYWORDS}

    has_specific_system = any(hit not in broad_systems for hit in system_hits)
    has_specific_action = any(hit not in broad_actions for hit in action_hits)
    return has_specific_system or has_specific_action

# ----------------------------------------------------------
# CHECK IF TENDER SHOULD BE EXCLUDED
# ----------------------------------------------------------
def should_exclude(
    text: str,
    strong_hits: list,
    system_hits: list | None = None,
    action_hits: list | None = None,
    phakathi_hits: list | None = None,
) -> tuple:
    """
    Check if tender matches negative keywords. Returns (should_exclude, reason).
    Override exclusion if ANY company has a signal: Mexel strong match,
    or Phakathi keywords match.
    """
    system_hits = system_hits or []
    action_hits = action_hits or []
    phakathi_hits = phakathi_hits or []

    has_mexel_strong_signal = len(strong_hits) > 0
    has_mexel_competence_signal = len(system_hits) > 0 and len(action_hits) > 0
    has_phakathi_signal = len(phakathi_hits) > 0

    has_any_company_signal = has_mexel_strong_signal or has_phakathi_signal

    for kw in NEGATIVE_KEYWORDS:
        if keyword_present(text, kw):
            if kw == "water supply" and has_mexel_competence_signal:
                continue
            if has_any_company_signal:
                return False, None
            return True, f"Excluded: '{kw}' (out of scope)"
    return False, None

# ----------------------------------------------------------
# SIMPLE SHORT TITLE MAKER
# ----------------------------------------------------------
def make_short_title(original_title: str) -> str:
    title = clean(original_title)
    remove_words = ["tender for", "appointment of", "for the", "supply and delivery of",
                    "supply & delivery", "supply of", "provision of", "services",
                    "service", "works", "project", "contract", "repairs", "maintenance"]

    for w in remove_words:
        title = title.replace(w, "")

    parts = [word.capitalize() for word in re.findall(r"[A-Za-z0-9]+", title)]
    return "_".join(parts[:4]) if parts else "General_Scope"

# ----------------------------------------------------------
# MAIN CLASSIFICATION FUNCTION
# ----------------------------------------------------------
def classify_tender(title: str, description: str) -> dict:
    text = clean(f"{title} {description}")

    # Brand check for Phakathi direct routing
    brand_match = [
        brand
        for brand in ["huawei", "reicon", "odacon"]
        if keyword_present(text, brand)
    ]
    if brand_match:
        phakathi_hits = keyword_hits(text, PHAKATHI_KEYWORDS)
        return {
            "category": "PHAKATHI",
            "reason": f"Direct Brand Routing: matched '{brand_match[0]}'",
            "short_title": make_short_title(title),
            "matched_keywords": build_matched_keywords(
                text, [], [], [], phakathi_hits
            ),
        }

    strong_hits = keyword_hits(text, STRONG_MATCH_KEYWORDS)
    system_hits = keyword_hits(text, SYSTEM_KEYWORDS)
    action_hits = keyword_hits(text, ACTION_KEYWORDS)
    phakathi_hits = keyword_hits(text, PHAKATHI_KEYWORDS)

    # 1. EXCLUSION CHECK FIRST
    excluded, exclude_reason = should_exclude(
        text, strong_hits, system_hits, action_hits, phakathi_hits,
    )
    if excluded:
        return {
            "category": "EXCLUDED",
            "reason": exclude_reason,
            "short_title": make_short_title(title),
        }

    # 2. PROFILE A: THE PRODUCT (Automatic Match - Mexel)
    if strong_hits:
        return {
            "category": "MEXEL",
            "reason": f"Strong Match (Profile A): {', '.join(strong_hits[:3])}",
            "short_title": make_short_title(title),
            "matched_keywords": build_matched_keywords(
                text, strong_hits, system_hits, action_hits, phakathi_hits,
            ),
        }

    # 3. PROFILE B: SYSTEM + ACTION (Must be paired - Mexel)
    if system_hits and action_hits and has_specific_profile_b_signal(system_hits, action_hits):
        return {
            "category": "MEXEL",
            "reason": f"Competence Match (Profile B): {system_hits[0]} + {action_hits[0]}",
            "short_title": make_short_title(title),
            "matched_keywords": build_matched_keywords(
                text, strong_hits, system_hits, action_hits, phakathi_hits,
            ),
        }

    # 4. PHAKATHI MATCH
    if phakathi_hits:
        return {
            "category": "PHAKATHI",
            "reason": f"Phakathi Match: {len(phakathi_hits)} keyword(s)",
            "short_title": make_short_title(title),
            "matched_keywords": build_matched_keywords(
                text, strong_hits, system_hits, action_hits, phakathi_hits
            ),
        }

    # 5. No match
    return {
        "category": "EXCLUDED",
        "reason": "Excluded: no matching profile for any company",
        "short_title": make_short_title(title),
        "matched_keywords": [],
    }
