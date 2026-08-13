# ==========================================================
# SCORING ENGINE
# Comprehensive tender scoring system
# Fit, Industry, Product Suitability
# ==========================================================


# ----------------------------------------------------------
# INDUSTRY SCORING WEIGHTS
# Higher = more valuable
# ----------------------------------------------------------
INDUSTRY_SCORES = {
    # HIGH VALUE (8-10)
    "power": 10,
    "power station": 10,
    "eskom": 10,
    "generation": 9,
    "mining": 9,
    "mine": 9,
    "petrochemical": 9,
    "refinery": 9,
    "sasol": 9,
    
    # MEDIUM-HIGH VALUE (6-8)
    "water utility": 8,
    "rand water": 8,
    "water board": 8,
    "municipal": 7,
    "municipality": 7,
    "hospital": 7,
    "healthcare": 7,
    "food": 7,
    "beverage": 7,
    "brewery": 7,
    
    # MEDIUM VALUE (4-6)
    "manufacturing": 6,
    "industrial": 6,
    "transport": 5,
    "transnet": 5,
    "port": 5,
    "logistics": 5,
    "university": 5,
    "education": 4,
    
    # LOWER VALUE (1-3)
    "retail": 3,
    "office": 2,
    "residential": 1,
}

# ----------------------------------------------------------
# MEXEL SUITABILITY KEYWORDS
# ----------------------------------------------------------
MEXEL_STRONG_FIT = [
    "cooling water", "cooling tower", "condenser",
    "boiler", "steam", "feedwater", "blowdown",
    "chemical dosing", "water treatment", "chemistry",
    "scale", "corrosion", "biocide", "mexel",
    "thermal", "heat rate", "efficiency",
    "monitoring", "iot", "sensor", "instrumentation",
]

MEXEL_MODERATE_FIT = [
    "water", "treatment", "chemical", "dosing",
    "industrial", "process", "plant",
]

# ----------------------------------------------------------
# PHAKATHI SUITABILITY KEYWORDS
# ----------------------------------------------------------
PHAKATHI_STRONG_FIT = [
    # Brand triggers
    "huawei", "reicon", "odacon",
    # Boiler chemistry & preservation
    "boiler chemistry", "boiler water", "boiler protection",
    "boiler treatment", "boiler preservation", "boiler water treatment", "boiler lay-up",
    "lay-up", "layup", "asset preservation",
    "flow-accelerated corrosion", "film forming amine", "film-forming amine",
    "ffa treatment", "steam drum", "steam circuit",
    # OT networking & SCADA
    "ot networking", "ot network", "ot networks", "operational technology",
    "scada", "industrial networking",
    "plc programming", "hmi programming", "automation system",
]


# ==========================================================
# SCORING FUNCTIONS
# ==========================================================

def calculate_fit_score(title: str, description: str, category: str) -> dict:
    """
    Calculate overall fit score (1-10) based on company alignment
    """
    text = f"{title} {description}".lower()

    score = 5  # Base score
    reasons = []

    # Category boost
    if category in ("MEXEL",):
        score += 2
        reasons.append("Mexel category match")
    elif category in ("PHAKATHI",):
        score += 2
        reasons.append("Phakathi category match")

    # Strong fit keywords
    mexel_strong = sum(1 for kw in MEXEL_STRONG_FIT if kw in text)
    phakathi_strong = sum(1 for kw in PHAKATHI_STRONG_FIT if kw in text)

    if mexel_strong >= 3:
        score += 2
        reasons.append(f"Strong Mexel alignment ({mexel_strong} keywords)")
    elif mexel_strong >= 1:
        score += 1
        reasons.append(f"Mexel alignment ({mexel_strong} keywords)")

    if phakathi_strong >= 3:
        score += 2
        reasons.append(f"Strong Phakathi alignment ({phakathi_strong} keywords)")
    elif phakathi_strong >= 1:
        score += 1
        reasons.append(f"Phakathi alignment ({phakathi_strong} keywords)")

    # Cap at 10
    score = min(10, max(1, score))

    return {
        "fit_score": score,
        "fit_reasons": reasons,
        "fit_grade": "A" if score >= 8 else "B" if score >= 6 else "C" if score >= 4 else "D"
    }


def calculate_industry_score(title: str, description: str, client: str) -> dict:
    """
    Score based on industry value (1-10)
    """
    text = f"{title} {description} {client}".lower()
    
    score = 5  # Default
    matched_industry = "General"
    
    for industry, ind_score in INDUSTRY_SCORES.items():
        if industry in text:
            if ind_score > score:
                score = ind_score
                matched_industry = industry.title()
    
    return {
        "industry_score": score,
        "industry_matched": matched_industry,
        "industry_grade": "A" if score >= 8 else "B" if score >= 6 else "C" if score >= 4 else "D"
    }


def calculate_suitability_scores(title: str, description: str, category: str = "MEXEL") -> dict:
    """
    Calculate suitability score based on company product keywords
    """
    text = f"{title} {description}".lower()

    # Mexel Score (base scoring for all categories)
    mexel_score = 0
    mexel_strong = sum(1 for kw in MEXEL_STRONG_FIT if kw in text)
    mexel_moderate = sum(1 for kw in MEXEL_MODERATE_FIT if kw in text)
    mexel_score = min(10, mexel_strong * 2 + mexel_moderate)

    return {
        "mexel_suitability": mexel_score,
        "mexel_fit": "Strong" if mexel_score >= 6 else "Moderate" if mexel_score >= 3 else "Weak",
        "company_category": category,
    }


# ==========================================================
# MASTER SCORING FUNCTION
# ==========================================================

def score_tender(title: str, description: str, client: str = "", 
                 closing_date: str = "", category: str = "Unknown") -> dict:
    """
    Generate complete tender score report
    Returns all scores and a composite priority score
    """
    
    if str(category or "").strip().upper() == "EXCLUDED":
        suitability = calculate_suitability_scores(title, description)
        return {
            "fit_score": 1,
            "fit_reasons": ["Tender excluded from scope"],
            "fit_grade": "D",
            "industry_score": 1,
            "industry_matched": "Excluded",
            "industry_grade": "D",
            **suitability,
            "composite": 1.0,
            "composite_score": 1.0,
            "priority": "LOW",
            "recommendation": "⏭️ EXCLUDED - Out of scope",
        }

    fit = calculate_fit_score(title, description, category)
    industry = calculate_industry_score(title, description, client)
    suitability = calculate_suitability_scores(title, description, category)
    
    # Composite priority score (weighted average)
    composite = (
        fit["fit_score"] * 0.60 +          # 60% weight
        industry["industry_score"] * 0.40  # 40% weight
    )
    
    priority = "HIGH" if composite >= 7 else "MEDIUM" if composite >= 5 else "LOW"
    
    return {
        # Individual scores
        **fit,
        **industry,
        **suitability,
        
        # Composite
        "composite": round(composite, 1),
        "composite_score": round(composite, 1),
        "priority": priority,
        
        # Recommendation
        "recommendation": generate_recommendation(fit, industry, suitability, composite, category)
    }


def generate_recommendation(fit, industry, suitability, composite, category="MEXEL"):
    """Generate actionable recommendation"""

    if category == "MEXEL":
        scope_label = "Mexel scope"
    elif category == "PHAKATHI":
        scope_label = "Phakathi scope"
    else:
        scope_label = "scope"

    if composite >= 8:
        return f"🔥 PRIORITY BID - Strong fit, pursue immediately"
    elif composite >= 6:
        return f"✅ RECOMMENDED - Good opportunity, prepare bid"
    elif composite >= 4:
        if suitability["mexel_suitability"] >= 6:
            return f"📋 CONSIDER - Core capability match despite moderate overall score"
        return f"📝 EVALUATE - May be worth pursuing if capacity allows"
    else:
        return f"⏭️ LOW PRIORITY - Does not align well with {scope_label}"


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test with sample tenders
    test_tenders = [
        {
            "title": "Supply of Cooling Water Treatment Chemicals",
            "description": "Supply and delivery of cooling water treatment chemicals for power station condensers including scale inhibitors and biocides for 3 year period",
            "client": "Eskom Holdings",
            "closing_date": "2025-12-15",
            "category": "MEXEL"
        },
        {
            "title": "Office Cleaning Services",
            "description": "Provision of cleaning services for municipal offices",
            "client": "Local Municipality",
            "closing_date": "2025-12-10",
            "category": "EXCLUDED"
        },
        {
            "title": "SCADA and OT Networking Upgrade for Boiler Plant",
            "description": "Supply, installation and telemetry design of Huawei SCADA systems and industrial networking for boiler steam circuits",
            "client": "Sasol Secunda",
            "closing_date": "2026-02-20",
            "category": "PHAKATHI"
        }
    ]
    
    print("=" * 60)
    print("TENDER SCORING ENGINE TEST")
    print("=" * 60)
    
    for t in test_tenders:
        print(f"\n📋 [{t['category']}] {t['title']}")
        print("-" * 40)
        
        scores = score_tender(
            title=t["title"],
            description=t["description"],
            client=t["client"],
            closing_date=t["closing_date"],
            category=t["category"]
        )
        
        print(f"   Fit Score:      {scores['fit_score']}/10 ({scores['fit_grade']})")
        print(f"   Industry Score: {scores['industry_score']}/10 ({scores['industry_matched']})")
        print(f"   Suitability:    {scores['mexel_suitability']}/10 ({scores['mexel_fit']})")
        print(f"   Company:        {scores['company_category']}")
        print(f"   ─────────────────────────────────")
        print(f"   COMPOSITE:      {scores['composite_score']}/10 → {scores['priority']}")
        print(f"   {scores['recommendation']}")
