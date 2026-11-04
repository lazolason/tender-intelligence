"""
MEXEL THERMAL EFFICIENCY SERVICES (TES) - KEYWORD RULES
Aligned with Mexel's core business: Thermal efficiency optimization through
Mexel®432 application, IoT dosing, thermal monitoring, and M&V protocols.

Target Industries:
1. Power Generation (500MW+ condenser circuits)
2. Mining & Smelters (furnace cooling, compressor loops)
3. Critical HVAC (data centers, large commercial cooling)

PHAKATHI KEYWORDS - REICON/ODACON chemistry, preservation and OT integration
"""

# =============================================================================
# MEXEL PROFILE
# =============================================================================

# PROFILE A: THE SERVICE (Automatic Match)
# Mexel brand, core technologies, and unique service offerings
STRONG_MATCH_KEYWORDS = [
    "mexel", "mexel 432", "mexel432",
    "condenser performance", "condenser efficiency", "vacuum recovery",
    "asme ptc 12.2", "legionella control", "legionella compliance",
    "cooling tower preservation",
]

# Require a cooling-water circuit AND a process/chemistry action. A site,
# equipment purchase or generic maintenance action does not establish fit.
SYSTEM_KEYWORDS = [
    "cooling tower", "cooling water", "cooling system", "circulating water",
    "turbine condenser", "condenser", "condensor", "heat exchanger",
    "furnace cooling", "compressor cooling", "precision cooling",
    "chiller", "chiller loop", "chiller loops", "mine refrigeration", "heat rejection loop",
    "closed cooling loop", "once through cooling", "recirculating cooling",
    "crac", "crah", "data center", "data centre", "server room",
]
ACTION_KEYWORDS = [
    "chemical dosing", "dosing", "water treatment", "water chemistry",
    "cooling water condition", "thermal monitoring", "thermal performance",
    "thermal efficiency", "heat transfer performance", "fouling", "scaling",
    "scale prevention", "biofouling", "biocide", "biocides",
    "biocidal", "biocidal properties", "online dosing", "on line dosing",
    "online dosing monitoring", "dosing monitoring", "antiscalant",
    "antiscalants", "surfactant", "surfactants", "legionella",
    "treatment chemicals", "treatment", "condenser vacuum", "cleanliness factor",
    "heat rate", "terminal temperature difference", "corrosion control",
    "corrosion inhibition", "scale control", "solids dispersion", "pulsed dosing",
    "performance verification", "thermal baseline", "water hygiene",
]
# Kept for existing callers. Generic site and procurement terms are no longer
# present in the positive lists above.
BROAD_SYSTEM_KEYWORDS = []
BROAD_ACTION_KEYWORDS = []

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
    "waste removal", "solid waste", "waste treatment facility",
    "alternative waste treatment", "refuse", "sludge removal",

    # Staffing/HR
    "resourcing", "personnel",
    # NOTE (2026-11-03): "appointment of" and "panel of service providers" were
    # removed from this list. They are South African procurement boilerplate that
    # appears in most in-scope tenders ("APPOINTMENT OF A SERVICE PROVIDER FOR
    # COOLING TOWER WATER TREATMENT..."), so they carried no scope signal and
    # acted as false-negative generators. Measured on the live eTenders feed they
    # rejected 409 and 135 tenders respectively before profile matching ran.
    # Narrow staffed-appointment scope is still covered by "resourcing"/"personnel".

    # Procurement notices and non-live opportunity records
    "regret letter", "publication of bidders", "publication of name of bidders",
    "publish bidder names", "bidder names", "bidders names", "validity extension",
    "tender cancellation", "tender cancelled", "cancellation", "regret",
    "tender validity",

    # Office/Building Maintenance (not industrial)
    "office furniture", "office equipment",
    "painting", "plumbing", "carpentry",
    "butterfly valve",
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
    "huawei", "reicon", "odacon",
    "boiler chemistry", "boiler water treatment", "steam cycle chemistry",
    "water steam cycle chemistry", "steam circuit treatment",
    "boiler preservation", "boiler lay-up", "steam cycle preservation",
    "feedwater treatment", "condensate treatment", "condensate polishing",
    "boiler chemical dosing", "steam cycle treatment", "water steam cycle treatment",
    "flow-accelerated corrosion", "film forming amine", "film-forming amine",
    "filming amine", "film forming agent", "ffa treatment",
    "chemical dosing", "dosing system", "dosing systems", "metering pump",
    "metering pumps", "flow verification", "flow meter", "flow meters",
    "flowmeter", "flowmeters", "process instrumentation", "process measurement",
    "industrial networking", "ot networking", "ot network", "ot networks",
    "industrial communications", "plant network", "plc programming",
    "hmi programming", "scada integration", "industrial automation",
    "industrial switching", "industrial ethernet", "plant connectivity",
    "remote telemetry", "cellular iot", "edge monitoring", "dosing skid",
    "dosing skids", "flow paced dosing", "injection system",
    # User-confirmed display supply opportunity (MWP3022CX is historical).
    "interactive led touch panel", "interactive led touch panels",
    "interactive display", "interactive displays", "interactive flat panel",
    "interactive flat panels", "touch screen monitor", "touchscreen monitor",
    "computer monitor", "computer monitors", "display monitor", "display monitors",
]

# Broad instrumentation and preservation words need a relevant circuit/system.
PISO_CIRCUITS = ["boiler", "feedwater", "condensate", "steam circuit", "steam cycle", "water steam cycle"]
PISO_CHEMISTRY_ACTIONS = ["chemistry", "chemical treatment", "corrosion inhibitor", "corrosion inhibitors", "corrosion inhibition", "preservation", "lay up", "layup", "iron transport", "corrosion product transport", "start up cleanup"]
PROCESS_CONTEXT = ["dosing", "process", "industrial", "cooling water", "boiler", "feedwater", "condensate", "steam cycle"]
PROCESS_INSTRUMENTS = ["conductivity", "pressure transmitter", "temperature sensor", "level measurement", "level sensor", "flow measurement", "online monitoring", "on line monitoring", "pump status", "plc interface", "plc interfaces", "historian connection", "historian interface", "scada interface"]
HUAWEI_SCOPE = ["network", "networking", "router", "routers", "switch", "switches", "switching", "firewall", "server", "servers", "connectivity", "enterprise integration", "ideahub", "idea hub", "interactive display", "touch panel", "touch panels"]
