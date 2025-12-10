# ==========================================================
# AI SCORING ENGINE
# Comprehensive tender scoring system
# Fit, Industry, Risk, Revenue, TES/Phakathi Suitability
# ==========================================================

import re
from datetime import datetime, timedelta

# ----------------------------------------------------------
# INDUSTRY SCORING WEIGHTS
# Higher = more valuable for TES/Phakathi
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
# RISK INDICATORS
# ----------------------------------------------------------
HIGH_RISK_KEYWORDS = [
    "urgent", "emergency", "immediate",
    "short deadline", "24 hour", "48 hour",
    "penalty", "liquidated damages", "ld clause",
    "performance bond", "bank guarantee",
    "joint venture required", "jv mandatory",
    "cidb 9", "cidb 8", "cidb 7",  # High CIDB grades
    "international experience", "5 year experience",
]

MEDIUM_RISK_KEYWORDS = [
    "cidb 6", "cidb 5",
    "3 year experience", "reference required",
    "site visit mandatory", "compulsory briefing",
    "subcontracting limited",
]

LOW_RISK_KEYWORDS = [
    "no cidb required", "all suppliers welcome",
    "emerging contractor", "smme", "bbbee",
    "local supplier", "local content",
]

# ----------------------------------------------------------
# REVENUE POTENTIAL INDICATORS
# ----------------------------------------------------------
REVENUE_KEYWORDS = {
    # HIGH REVENUE (likely > R5M)
    "high": [
        "multi-year", "3 year", "5 year", "framework",
        "panel", "r10", "r20", "r50", "r100",
        "million", "plant wide", "site wide",
        "power station", "all units",
    ],
    # MEDIUM REVENUE (R500K - R5M)
    "medium": [
        "annual", "12 month", "maintenance contract",
        "service level agreement", "sla",
        "r1", "r2", "r5",
    ],
    # LOW REVENUE (< R500K)
    "low": [
        "once-off", "ad-hoc", "quotation",
        "small", "minor", "r100", "r200", "r500",
        "thousand",
    ]
}

# ----------------------------------------------------------
# TES SUITABILITY KEYWORDS
# ----------------------------------------------------------
TES_STRONG_FIT = [
    "cooling water", "cooling tower", "condenser",
    "boiler", "steam", "feedwater", "blowdown",
    "chemical dosing", "water treatment", "chemistry",
    "scale", "corrosion", "biocide", "mexel",
    "thermal", "heat rate", "efficiency",
    "monitoring", "iot", "sensor", "instrumentation",
]

TES_MODERATE_FIT = [
    "water", "treatment", "chemical", "dosing",
    "industrial", "process", "plant",
]

# ----------------------------------------------------------
# PHAKATHI SUITABILITY KEYWORDS
# ----------------------------------------------------------
PHAKATHI_STRONG_FIT = [
    "pump", "impeller", "shaft", "bearing",
    "white metal", "babbitt", "casting",
    "machining", "fabrication", "welding",
    "gearbox", "coupling", "mechanical seal",
    "refurbishment", "overhaul", "repair",
    "switchgear", "mcc", "panel", "distribution",
]

PHAKATHI_MODERATE_FIT = [
    "mechanical", "rotating", "equipment",
    "maintenance", "workshop", "spares",
    "valve", "pipe", "flange",
]


# ==========================================================
# SCORING FUNCTIONS
# ==========================================================

def calculate_fit_score(title: str, description: str, category: str) -> dict:
    """
    Calculate overall fit score (1-10) based on TES/Phakathi alignment
    """
    text = f"{title} {description}".lower()
    
    score = 5  # Base score
    reasons = []
    
    # Category boost
    if category == "TES":
        score += 2
        reasons.append("TES category match")
    elif category == "Phakathi":
        score += 2
        reasons.append("Phakathi category match")
    elif category == "Both":
        score += 3
        reasons.append("Dual TES+Phakathi opportunity")
    
    # Strong fit keywords
    tes_strong = sum(1 for kw in TES_STRONG_FIT if kw in text)
    phakathi_strong = sum(1 for kw in PHAKATHI_STRONG_FIT if kw in text)
    
    if tes_strong >= 3:
        score += 2
        reasons.append(f"Strong TES alignment ({tes_strong} keywords)")
    elif tes_strong >= 1:
        score += 1
        reasons.append(f"TES alignment ({tes_strong} keywords)")
    
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


def calculate_risk_score(title: str, description: str, closing_date: str = "") -> dict:
    """
    Risk assessment (1-10, lower = higher risk)
    10 = Low risk, 1 = High risk
    """
    text = f"{title} {description}".lower()
    
    score = 7  # Default medium-low risk
    risks = []
    
    # High risk indicators
    high_risk_count = sum(1 for kw in HIGH_RISK_KEYWORDS if kw in text)
    if high_risk_count >= 2:
        score -= 4
        risks.append(f"Multiple high-risk factors ({high_risk_count})")
    elif high_risk_count == 1:
        score -= 2
        risks.append("High-risk factor detected")
    
    # Medium risk indicators
    med_risk_count = sum(1 for kw in MEDIUM_RISK_KEYWORDS if kw in text)
    if med_risk_count >= 2:
        score -= 2
        risks.append(f"Medium-risk factors ({med_risk_count})")
    elif med_risk_count == 1:
        score -= 1
        risks.append("Medium-risk factor detected")
    
    # Low risk indicators (positive)
    low_risk_count = sum(1 for kw in LOW_RISK_KEYWORDS if kw in text)
    if low_risk_count >= 1:
        score += 1
        risks.append("Low-barrier entry indicators")
    
    # Deadline risk
    if closing_date:
        try:
            close = datetime.strptime(closing_date, "%Y-%m-%d")
            days_left = (close - datetime.now()).days
            if days_left < 7:
                score -= 2
                risks.append(f"Tight deadline ({days_left} days)")
            elif days_left < 14:
                score -= 1
                risks.append(f"Short timeline ({days_left} days)")
        except:
            pass
    
    score = min(10, max(1, score))
    
    return {
        "risk_score": score,
        "risk_factors": risks,
        "risk_level": "Low" if score >= 7 else "Medium" if score >= 4 else "High"
    }


def calculate_revenue_score(title: str, description: str) -> dict:
    """
    Revenue potential score (1-10)
    """
    text = f"{title} {description}".lower()
    
    score = 5  # Default medium
    indicators = []
    
    # Check for value mentions
    value_match = re.search(r'r\s*(\d+)\s*(million|m\b)', text)
    if value_match:
        value = int(value_match.group(1))
        if value >= 10:
            score = 10
            indicators.append(f"High value: R{value}M+")
        elif value >= 5:
            score = 8
            indicators.append(f"Good value: R{value}M")
        elif value >= 1:
            score = 6
            indicators.append(f"Moderate value: R{value}M")
    
    # High revenue keywords
    high_count = sum(1 for kw in REVENUE_KEYWORDS["high"] if kw in text)
    if high_count >= 2:
        score = max(score, 8)
        indicators.append("Multi-year/framework opportunity")
    
    # Low revenue keywords
    low_count = sum(1 for kw in REVENUE_KEYWORDS["low"] if kw in text)
    if low_count >= 2:
        score = min(score, 4)
        indicators.append("Small/once-off opportunity")
    
    score = min(10, max(1, score))
    
    return {
        "revenue_score": score,
        "revenue_indicators": indicators,
        "revenue_potential": "High" if score >= 7 else "Medium" if score >= 4 else "Low"
    }


def calculate_suitability_scores(title: str, description: str) -> dict:
    """
    Calculate TES and Phakathi suitability scores separately
    """
    text = f"{title} {description}".lower()
    
    # TES Score
    tes_score = 0
    tes_strong = sum(1 for kw in TES_STRONG_FIT if kw in text)
    tes_moderate = sum(1 for kw in TES_MODERATE_FIT if kw in text)
    tes_score = min(10, tes_strong * 2 + tes_moderate)
    
    # Phakathi Score
    phakathi_score = 0
    phakathi_strong = sum(1 for kw in PHAKATHI_STRONG_FIT if kw in text)
    phakathi_moderate = sum(1 for kw in PHAKATHI_MODERATE_FIT if kw in text)
    phakathi_score = min(10, phakathi_strong * 2 + phakathi_moderate)
    
    return {
        "tes_suitability": tes_score,
        "tes_fit": "Strong" if tes_score >= 6 else "Moderate" if tes_score >= 3 else "Weak",
        "phakathi_suitability": phakathi_score,
        "phakathi_fit": "Strong" if phakathi_score >= 6 else "Moderate" if phakathi_score >= 3 else "Weak",
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
    risk = calculate_risk_score(title, description, closing_date)
    revenue = calculate_revenue_score(title, description)
    suitability = calculate_suitability_scores(title, description)
    
    # Composite priority score (weighted average)
    composite = (
        fit["fit_score"] * 0.30 +          # 30% weight
        industry["industry_score"] * 0.20 + # 20% weight
        risk["risk_score"] * 0.15 +         # 15% weight
        revenue["revenue_score"] * 0.20 +   # 20% weight
        max(suitability["tes_suitability"], suitability["phakathi_suitability"]) * 0.15  # 15% weight
    )
    
    priority = "HIGH" if composite >= 7 else "MEDIUM" if composite >= 5 else "LOW"
    
    return {
        # Individual scores
        **fit,
        **industry,
        **risk,
        **revenue,
        **suitability,
        
        # Composite
        "composite": round(composite, 1),
        "composite_score": round(composite, 1),
        "priority": priority,
        
        # Recommendation
        "recommendation": generate_recommendation(fit, industry, risk, revenue, suitability, composite)
    }


def generate_recommendation(fit, industry, risk, revenue, suitability, composite):
    """Generate actionable recommendation"""
    
    if composite >= 8:
        return "🔥 PRIORITY BID - Strong fit, pursue immediately"
    elif composite >= 6:
        if risk["risk_level"] == "High":
            return "⚠️ REVIEW CAREFULLY - Good opportunity but high risk factors"
        return "✅ RECOMMENDED - Good opportunity, prepare bid"
    elif composite >= 4:
        if suitability["tes_suitability"] >= 6 or suitability["phakathi_suitability"] >= 6:
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
            "category": "TES"
        },
        {
            "title": "Pump Refurbishment and Mechanical Repairs",
            "description": "Refurbishment of centrifugal pumps including impeller replacement and white metal bearing recasting",
            "client": "City of Johannesburg",
            "closing_date": "2025-12-20",
            "category": "Phakathi"
        },
        {
            "title": "Office Cleaning Services",
            "description": "Provision of cleaning services for municipal offices",
            "client": "Local Municipality",
            "closing_date": "2025-12-10",
            "category": "Unknown"
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
        print(f"   Risk Score:     {scores['risk_score']}/10 ({scores['risk_level']} risk)")
        print(f"   Revenue Score:  {scores['revenue_score']}/10 ({scores['revenue_potential']})")
        print(f"   TES Fit:        {scores['tes_suitability']}/10 ({scores['tes_fit']})")
        print(f"   Phakathi Fit:   {scores['phakathi_suitability']}/10 ({scores['phakathi_fit']})")
        print(f"   ─────────────────────────────────")
        print(f"   COMPOSITE:      {scores['composite_score']}/10 → {scores['priority']}")
        print(f"   {scores['recommendation']}")
