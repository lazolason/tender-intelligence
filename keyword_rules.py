"""
MEXEL THERMAL EFFICIENCY SERVICES (TES) - KEYWORD RULES
Aligned with Mexel's core business: Thermal efficiency optimization through
Mexel®432 application, IoT dosing, thermal monitoring, and M&V protocols.

Target Industries:
1. Power Generation (500MW+ condenser circuits)
2. Mining & Smelters (furnace cooling, compressor loops)
3. Critical HVAC (data centers, large commercial cooling)

FLOWTECH KEYWORDS - Pump refurbishment and slurry handling

PHAKATHI KEYWORDS - Machining, component manufacture, pump spares
"""

# =============================================================================
# MEXEL PROFILE
# =============================================================================

# PROFILE A: THE SERVICE (Automatic Match)
# Mexel brand, core technologies, and unique service offerings
STRONG_MATCH_KEYWORDS = [
    # Brand & Product
    "mexel", "mexel 432", "mexel432", "mexsteam", "mexsteam 100",
    "film forming amine", "filming amine", "film forming agent", "ffa",
    "antiscalant", "oxidizing biocide", "surfactant",

    # Core Service Metrics (unique to TES)
    "condenser performance", "condenser efficiency",
    "thermal efficiency", "heat rate",
    "back pressure", "vacuum recovery",
    "megawatt gain", "mw gain", "power gain",

    # Service Delivery
    "iot dosing", "automated dosing", "precision dosing",

    # Validation & Standards
    "asme ptc 12.2", "measurement and verification", "m&v protocol",

    # Data Center Specific
    "pue", "power usage effectiveness",
    "legionella control", "legionella compliance"
]

# PROFILE B1: THE SYSTEM (Must be paired with an Action)
# Industrial cooling systems where Mexel provides efficiency services
SYSTEM_KEYWORDS = [
    # Power Generation
    "power plant", "power station", "generating unit", "generation facility",
    "turbine condenser", "condenser", "condensor",
    "cooling tower", "cooling water", "cooling system", "wet cooling", "wet-cooled",
    "closed loop", "circulating water",

    # Specific Sites (Critical for Matches without "Power Station")
    "medupi", "matla", "grootvlei", "kusile", "kendal", "majuba", "tutuka",
    "arnot", "hendrina", "camden", "komati", "lethabo", "duvha",


    # Heat Transfer Equipment
    "heat exchanger", "chiller", "cooling coil",
    "reverse osmosis", "ro system",

    # Mining & Smelters
    "smelter", "furnace", "furnace cooling",
    "compressor", "compressor cooling",

    # Data Center / Critical HVAC
    "crac", "crah", "chr",
    "data center", "data centre",
    "computer room", "server room",
    "precision cooling", "close control cooling",
    "mission critical cooling",

    # Generic Industrial (New)
    "industrial system", "facility", "infrastructure"
]

# PROFILE B2: THE ACTION (Must be paired with a System)
# Services and outcomes that Mexel delivers
ACTION_KEYWORDS = [
    # Efficiency & Performance
    "efficiency", "thermal efficiency", "optimization", "optimisation",
    "performance improvement", "performance restoration",
    "efficiency improvement", "efficiency restoration",

    # Service Delivery
    "dosing", "treatment", "application",
    "monitoring", "performance tracking",
    "service", "servicing",
    "maintenance", "operation",

    # Supply & Installation (for dosing systems)
    "supply", "delivery", "installation",

    # Problems Mexel Solves
    "fouling", "scaling", "deposition",
    "fouling prevention", "scale prevention",
    "corrosion", "corrosion prevention",

    # Service Process
    "baseline", "intervention", "restoration", "restore",
    "verification", "validation",
    "chemistry", "analysis",

    # Outcomes
    "thermal performance", "heat transfer",
    "capacity restoration", "capacity recovery",
    "water quality", "water treatment",

    # New Growth Actions
    "retrofit", "refurbishment", "epc", "engineering", "resin", "desulphurization", "fgd"
]

# PROFILE B GUARDRAILS
# Broad site references and generic commercial actions are not enough on their own.
BROAD_SYSTEM_KEYWORDS = [
    "power plant", "power station", "generating unit", "generation facility",
    "medupi", "matla", "grootvlei", "kusile", "kendal", "majuba", "tutuka",
    "arnot", "hendrina", "camden", "komati", "lethabo", "duvha",
    "industrial system", "facility", "infrastructure"
]

BROAD_ACTION_KEYWORDS = [
    "service", "servicing", "maintenance", "operation",
    "supply", "delivery", "installation",
    "retrofit", "refurbishment", "epc", "engineering",
    "monitoring", "performance tracking"
]

# EXCLUSIONS (Refined for TES Business)
# Exclude tenders that are clearly outside Mexel's service scope
NEGATIVE_KEYWORDS = [
    # Construction & Infrastructure (not efficiency services)
    "construction of", "building of", "civil works",
    "structural steel", "paving", "road",
    "dam construction", "hydroelectric",

    # Building HVAC (NOT industrial/data center cooling)
    "split unit", "office air conditioning", "building hvac",
    "building air conditioning", "residential hvac", "domestic",

    # Non-cooling Services
    "security service", "security guarding",
    "cleaning service", "garden service",
    "hygiene service",
    "consulting engineer", "transaction advisor", "panel of",
    "facilities maintenance",
    "vehicle", "vehicles", "fleet", "transport", "shuttle",

    # Electrical/Power Distribution (not thermal efficiency)
    "switchgear", "transformer", "substation", "transmission",
    "electrical installation", "power distribution",

    # Water/Wastewater Treatment (not cooling efficiency)
    "potable water", "drinking water", "water supply",
    "sewage", "wastewater treatment",
    "waste removal", "refuse", "sludge removal",

    # Staffing/HR
    "resourcing", "personnel",
    "appointment of", "panel of service providers",

    # Procurement notices and non-live opportunity records
    "regret letter", "publication of bidders", "publication of name of bidders",
    "publish bidder names", "bidder names", "validity extension",
    "tender cancellation", "tender cancelled", "cancellation", "regret",
    "tender validity",

    # Office/Building Maintenance (not industrial)
    "office furniture", "office equipment",
    "painting", "plumbing", "carpentry",
    "steel supply", "bearings supply",

    # Generic maintenance-only boiler work tends to be mechanical, not TES chemistry scope
    "boiler maintenance",

    # Environmental, lab, and adjacent monitoring scopes outside Mexel TES
    "dewatering", "laboratory equipment", "ash disposal",
    "surface water monitoring", "ground and surface water",
    "dust monitoring", "noise monitoring"
]

# Backward compatibility for legacy scripts/tests.
EXCLUDE_KEYWORDS = NEGATIVE_KEYWORDS

# =============================================================================
# PHAKATHI PROFILE - Boilers, boiler chemistry, OT networking, SCADA, & agencies
# =============================================================================

PHAKATHI_KEYWORDS = [
    # Brand Triggers & Agencies (highest priority — any match routes directly to PHAKATHI)
    "huawei", "reicon", "odacon",

    # Boilers & Steam Chemistry (compound phrases only — avoids false positives)
    "boiler chemistry", "boiler water", "boiler protection",
    "boiler treatment", "boiler preservation", "boiler water treatment",
    "lay-up", "layup", "asset preservation",
    "flow-accelerated corrosion", "film forming amine", "film-forming amine",
    "ffa treatment", "steam drum", "steam circuit", "boiler lay-up",

    # OT Networking & SCADA
    "ot networking", "ot network", "ot networks", "operational technology",
    "scada", "industrial networking",
    "plc programming", "hmi programming", "automation system",
]
