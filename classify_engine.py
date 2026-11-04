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
    PISO_CIRCUITS, PISO_CHEMISTRY_ACTIONS, PROCESS_CONTEXT, PROCESS_INSTRUMENTS, HUAWEI_SCOPE,
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
    keyword = clean(keyword)
    if not keyword:
        return False
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

    return sorted(matched)


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
    return has_specific_system and has_specific_action

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
def _classify_legacy(title: str, description: str) -> dict:
    text = clean(f"{title} {description}")

    # A brand name cannot turn an explicit cancellation/award notice into a
    # live opportunity. Use the headline so ordinary contractual conditions in
    # the description do not suppress a live advert.
    notice_keywords = (
        "regret letter", "publication of bidders", "publication of name of bidders",
        "bidder names", "bidders names", "validity extension", "tender validity",
        "tender cancellation", "tender cancelled", "cancellation",
        "notification of award", "notification of awarded", "award notice",
    )
    for notice in notice_keywords:
        if keyword_present(clean(title), notice):
            return {"category": "EXCLUDED", "reason": f"Excluded: notice '{notice}'",
                    "short_title": make_short_title(title), "matched_keywords": []}

    # Headline scope wins over incidental equipment/brand names in attachments.
    # These are works contracts, not the process and supply scopes we pursue.
    works_hits = keyword_hits(clean(title), [
        "refurbishment", "refurbishing", "retubing", "high pressure jetting",
        "civil structures", "cathodic protection", "floodlighting",
        "compressor service", "compressor maintenance",
    ])
    if works_hits:
        return {"category": "EXCLUDED", "reason": f"Excluded: works scope '{works_hits[0]}'",
                "short_title": make_short_title(title), "matched_keywords": []}

    # Brand check for Phakathi direct routing
    brand_match = [
        brand
        for brand in ["huawei", "reicon", "odacon"]
        if keyword_present(text, brand)
    ]
    # Huawei is an infrastructure/specified display route, not a general product remit.
    if "huawei" in brand_match and not keyword_hits(text, HUAWEI_SCOPE):
        brand_match.remove("huawei")
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
    phakathi_hits = keyword_hits(text, [kw for kw in PHAKATHI_KEYWORDS if kw != "huawei"])
    circuit_hits = keyword_hits(text, PISO_CIRCUITS)
    chemistry_hits = keyword_hits(text, PISO_CHEMISTRY_ACTIONS)
    if circuit_hits and chemistry_hits:
        phakathi_hits += circuit_hits + chemistry_hits
    context_hits = keyword_hits(text, PROCESS_CONTEXT)
    instrument_hits = keyword_hits(text, PROCESS_INSTRUMENTS)
    if context_hits and instrument_hits:
        # Explicit cooling-water monitoring belongs to Mexel; generic dosing/
        # instrumentation projects remain under PISO.
        if system_hits and keyword_hits(text, ["cooling water", "cooling tower", "circulating water"]):
            action_hits += instrument_hits
        else:
            phakathi_hits += context_hits + instrument_hits

    if keyword_hits(text, ["cooling water", "cooling tower", "circulating water"]) and keyword_hits(text, ["monitor", "monitors", "monitoring"]):
        action_hits += ["cooling-water monitoring"]

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

    # Boiler/steam chemistry and generic FFA terms belong to PISO's chemistry
    # profile. Explicit Mexel product terms above retain their own routing.
    if phakathi_hits:
        return {
            "category": "PHAKATHI",
            "reason": f"Phakathi Match: {len(phakathi_hits)} keyword(s)",
            "short_title": make_short_title(title),
            "matched_keywords": build_matched_keywords(text, [], [], [], phakathi_hits),
        }

    # 5. No match
    return {
        "category": "EXCLUDED",
        "reason": "Excluded: no matching profile for any company",
        "short_title": make_short_title(title),
        "matched_keywords": [],
    }


# The legacy category remains a storage/scoring compatibility field. Portfolio
# matches are independent: one opportunity can carry several relevant scopes.
PORTFOLIO_FIELDS = ("portfolios", "companies", "capabilities", "portfolio_matches")


def classify_tender(title: str, description: str) -> dict:
    result = _classify_legacy(title, description)
    matches = []
    text = clean(f"{title} {description}")
    if result["category"] != "EXCLUDED":
        cooling = keyword_hits(text, SYSTEM_KEYWORDS)
        actions = keyword_hits(text, ACTION_KEYWORDS)
        cooling_monitoring = keyword_hits(text, ["cooling water", "cooling tower", "circulating water"]) and keyword_hits(text, ["monitor", "monitors", "monitoring"])
        mexel_hits = keyword_hits(text, STRONG_MATCH_KEYWORDS)
        if mexel_hits or (cooling and (actions or cooling_monitoring)):
            capabilities = []
            groups = {
                "Cooling-water chemistry": ["mexel", "surfactant", "surfactants", "treatment", "chemistry", "biocidal", "biofouling", "biocide", "scale control", "corrosion control"],
                "Dosing and process monitoring": ["dosing", "monitoring", "monitor", "monitors", "telemetry"],
                "Thermal-performance review": ["condenser performance", "condenser efficiency", "thermal performance", "thermal efficiency", "heat rate", "vacuum", "asme ptc 12.2"],
                "Cooling-tower preservation": ["cooling tower preservation"],
            }
            for capability, words in groups.items():
                if keyword_hits(text, words):
                    capabilities.append(capability)
            matches.append({"portfolio": "MEXEL", "capabilities": capabilities or ["Cooling-water treatment"], "matched_keywords": sorted(set(mexel_hits + cooling + actions)), "reason": "Cooling-water product/process scope"})

        chemistry_words = ["reicon", "odacon", "film forming amine", "filming amine", "film forming agent", "ffa treatment", "flow accelerated corrosion", "boiler chemistry", "boiler water treatment", "feedwater treatment", "condensate treatment", "steam cycle treatment", "boiler chemical dosing", "boiler preservation", "boiler lay-up", "steam cycle preservation", "water steam cycle treatment", "water steam cycle chemistry", "steam cycle chemistry", "steam circuit treatment", "condensate polishing"]
        chemistry_hits = keyword_hits(text, chemistry_words)
        circuit_hits = keyword_hits(text, PISO_CIRCUITS)
        chemistry_actions = keyword_hits(text, PISO_CHEMISTRY_ACTIONS)
        if chemistry_hits or (circuit_hits and chemistry_actions):
            preservation = keyword_hits(text, ["preservation", "lay up", "layup", "standby", "shutdown"])
            capabilities = ["Water and steam-cycle chemistry"]
            if preservation:
                capabilities.append("Corrosion protection and preservation")
            matches.append({"portfolio": "REICON_ODACON", "capabilities": capabilities, "matched_keywords": sorted(set(chemistry_hits + circuit_hits + chemistry_actions)), "reason": "REICON/ODACON chemistry scope; delivered through Phakathi"})

        equipment_words = [kw for kw in PHAKATHI_KEYWORDS if kw not in chemistry_words and kw not in ["reicon", "odacon", "boiler preservation", "boiler lay-up", "steam cycle preservation", "water steam cycle treatment", "water steam cycle chemistry", "steam cycle chemistry", "steam circuit treatment", "condensate polishing", "boiler chemical dosing", "film-forming amine"]]
        equipment_hits = keyword_hits(text, equipment_words)
        if "huawei" in equipment_hits and not keyword_hits(text, HUAWEI_SCOPE):
            equipment_hits.remove("huawei")
        instruments = keyword_hits(text, PROCESS_INSTRUMENTS) if keyword_hits(text, PROCESS_CONTEXT) else []
        if equipment_hits or instruments:
            matches.append({"portfolio": "PHAKATHI", "capabilities": ["Equipment, instrumentation and integration"], "matched_keywords": sorted(set(equipment_hits + instruments)), "reason": "Specified equipment or process-integration scope"})

    result["portfolio_matches"] = matches
    result["portfolios"] = [match["portfolio"] for match in matches]
    result["companies"] = list(dict.fromkeys("Mexel" if name == "MEXEL" else "Phakathi" for name in result["portfolios"]))
    result["capabilities"] = sorted({capability for match in matches for capability in match["capabilities"]})
    return result


def portfolio_metadata(title: str, description: str) -> dict:
    classification = classify_tender(title, description)
    return {key: classification[key] for key in PORTFOLIO_FIELDS}
