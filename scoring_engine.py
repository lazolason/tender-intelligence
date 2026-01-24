# ==========================================================
# SCORING ENGINE
# Comprehensive tender scoring system
# Fit, Industry, Mexel product Suitability
# ==========================================================


# ----------------------------------------------------------
# INDUSTRY SCORING WEIGHTS
# Higher = more valuable for Mexel
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


# ==========================================================
# SCORING FUNCTIONS
# ==========================================================

def calculate_fit_score(title: str, description: str, category: str) -> dict:
    """
    Calculate overall fit score (1-10) based on Mexel alignment
    """
    text = f"{title} {description}".lower()

    score = 5  # Base score
    reasons = []

    # Category boost
    if category in ("MEXEL",):
        score += 2
        reasons.append("Mexel category match")

    # Strong fit keywords
    mexel_strong = sum(1 for kw in MEXEL_STRONG_FIT if kw in text)

    if mexel_strong >= 3:
        score += 2
        reasons.append(f"Strong Mexel alignment ({mexel_strong} keywords)")
    elif mexel_strong >= 1:
        score += 1
        reasons.append(f"Mexel alignment ({mexel_strong} keywords)")

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


def calculate_suitability_scores(title: str, description: str) -> dict:
    """
    Calculate Mexel suitability score
    """
    text = f"{title} {description}".lower()

    # Mexel Score
    mexel_score = 0
    mexel_strong = sum(1 for kw in MEXEL_STRONG_FIT if kw in text)
    mexel_moderate = sum(1 for kw in MEXEL_MODERATE_FIT if kw in text)
    mexel_score = min(10, mexel_strong * 2 + mexel_moderate)

    return {
        "mexel_suitability": mexel_score,
        "mexel_fit": "Strong" if mexel_score >= 6 else "Moderate" if mexel_score >= 3 else "Weak",
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
    
    fit = calculate_fit_score(title, description, category)
    industry = calculate_industry_score(title, description, client)
    suitability = calculate_suitability_scores(title, description)
    
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
        "recommendation": generate_recommendation(fit, industry, suitability, composite)
    }

def generate_recommendation(fit, industry, suitability, composite):
    """Generate actionable recommendation"""

    if composite >= 8:
        return "🔥 PRIORITY BID - Strong fit, pursue immediately"
    elif composite >= 6:
        return "✅ RECOMMENDED - Good opportunity, prepare bid"
    elif composite >= 4:
        if suitability["mexel_suitability"] >= 6:
            return "📋 CONSIDER - Core capability match despite moderate overall score"
        return "📝 EVALUATE - May be worth pursuing if capacity allows"
    else:
        return "⏭️ LOW PRIORITY - Does not align well with capabilities"


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
        }
    ]
    
    print("=" * 60)
    print("TENDER SCORING ENGINE TEST")
    print("=" * 60)
    
    for t in test_tenders:
        print(f"\n📋 {t['title']}")
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
        print(f"   Mexel Suitability: {scores['mexel_suitability']}/10 ({scores['mexel_fit']})")
        print(f"   ─────────────────────────────────")
        print(f"   COMPOSITE:      {scores['composite_score']}/10 → {scores['priority']}")
        print(f"   {scores['recommendation']}")
