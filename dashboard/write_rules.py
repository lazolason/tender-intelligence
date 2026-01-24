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
    "condensate polisher", "condensate polishing"
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
    "demineralisation", "demineralization", "reverse osmosis", "ro plant"
]

# PROFILE B2: THE ACTION (Must be paired with a System)
# Relevant services or chemical applications.
ACTION_KEYWORDS = [
    "treatment", "chemical", "dosing", "cleaning", "descaling",
    "efficiency", "fouling", "passivation", "preservation",
    "water quality", "chemistry", "purification", "optimisation",
    "optimization", "additive",
    # Maintenance actions (Safe because they require a System pairing)
    "maintenance", "repair", "servicing", "overhaul", "refurbishment"
]

# EXCLUSIONS (Refined)
# Targeted exclusions for things that often get confused with water treatment.
NEGATIVE_KEYWORDS = [
    "construction of", "building of", "civil works",
    "structural steel", "paving", "road",
    "hvac", "air conditioning", "ventilation", "split unit",
    "security service", "cleaning service", "garden service", "hygiene",
    "consulting engineer", "transaction advisor", "panel of",
    "vehicle", "fleet", "transport", "shuttle",
    "hydroelectric", "dam construction",
    "commissioning support", "resourcing", "personnel",
    "switchgear", "transformer", "substation", "transmission",
    "waste removal", "refuse", "sludge removal",
    "general building maintenance"
]
