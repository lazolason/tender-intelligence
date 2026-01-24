"""
STRICT COMPETENCE RULES (PHASE 2)
Aligned with Mexel competencies: Water Treatment & Thermal Efficiency.
"""

# PROFILE A: THE PRODUCT (Automatic Match)
# Specific chemical technologies or brand names.
STRONG_MATCH_KEYWORDS = [
    "mexel", "mexel 432", "mexel432", "mexsteam", "mexsteam 100",
    "film forming amine", "filming amine", "film forming agent", "ffa",
    "scale inhibitor", "antiscalant", "anti-scalant",
    "corrosion inhibitor", "corrosion barrier",
    "oxygen scavenger",
    "non-oxidizing biocide", "biodispersant",
    "condensate polisher", "condensate polishing",
    # Highly specific technical terms
    "surfactant", "legionella", "asme ptc 12.2"
]

# PROFILE B1: THE SYSTEM (Must be paired with an Action)
# Specific industrial water systems.
SYSTEM_KEYWORDS = [
    "cooling tower", "cooling water", "cooling system", "closed loop",
    "condenser", "condensor",
    "boiler", "steam generator", "steam drum",
    "feedwater", "feed water",
    "heat exchanger", "chiller",
    "clarifier", "raw water treatment", "effluent treatment",
    "demineralisation", "demineralization", "reverse osmosis", "ro plant",
    # Data center / critical infrastructure cooling
    "crac", "crah", "chr",  # Computer Room Air Conditioning/Handler
    "data center", "data centre",
    "computer room", "server room",
    "precision cooling", "close control cooling"
]

# PROFILE B2: THE ACTION (Must be paired with a System)
# Relevant services or chemical applications.
ACTION_KEYWORDS = [
    "treatment", "chemical", "dosing", "cleaning", "descaling",
    "efficiency", "fouling", "passivation", "preservation",
    "water quality", "chemistry", "purification", "optimisation",
    "optimization", "additive",
    # Data center efficiency metrics
    "pue", "power usage effectiveness",
    "vacuum recovery", "thermal efficiency",
    "condenser efficiency",
    # Maintenance actions (Safe because they require a System pairing)
    "maintenance", "repair", "servicing", "overhaul", "refurbishment"
]

# EXCLUSIONS (Refined)
# Targeted exclusions for things that often get confused with water treatment.
# NOTE: "hvac" removed - too broad, excludes data center CRAC/CRAH systems
NEGATIVE_KEYWORDS = [
    "construction of", "building of", "civil works",
    "structural steel", "paving", "road",
    # Building HVAC (NOT data center precision cooling)
    "split unit", "office air conditioning", "building hvac", 
    "building air conditioning", "ventilation",
    "security service", "cleaning service", "garden service", "hygiene",
    "consulting engineer", "transaction advisor", "panel of",
    "vehicle", "fleet", "transport", "shuttle",
    "hydroelectric", "dam construction",
    "commissioning support", "resourcing", "personnel",
    "switchgear", "transformer", "substation", "transmission",
    "waste removal", "refuse", "sludge removal",
    "general building maintenance"
]
