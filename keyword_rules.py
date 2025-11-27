# ================================================
# KEYWORD RULES FOR TENDER CLASSIFICATION ENGINE
# TES + Phakathi + Switchgear Logic (Locked)
# ================================================

TES_KEYWORDS = [
    # Cooling water / Condenser / Thermal
    "cooling water", "cooling tower", "condenser", "heat exchanger",
    "fouling", "scaling", "cooling circuit", "thermal efficiency",
    "heat rate", "heat balance", "cw system", "chiller",

    # Steam / Boilers / Water-Steam Cycle
    "steam", "boiler", "boiler maintenance", "blowdown", "deaerator",
    "superheater", "condensate", "feedwater", "boiler water treatment",

    # Chemistry / Dosing / Water Treatment
    "chemical dosing", "water treatment", "chemicals supply",
    "scale inhibitor", "corrosion inhibitor", "dispersant", "surfactant",
    "biocide", "non-biocidal", "film forming amine", "ffa",
    "mexel", "mexel432", "mexsteam", "dosing system",

    # Monitoring / IoT
    "water quality monitoring", "conductivity", "ph control",
    "orp", "chemical injection", "sensor", "thermal monitoring"
]

# ===========================================================

PHAKATHI_KEYWORDS = [
    # Mechanical Supply & Rotating Equipment
    "pump", "impeller", "shaft", "pump refurbishment", "mechanical seals",
    "gearbox", "couplings", "motor", "rotating equipment", "pump spares",
    "alignment", "impeller casting", "pump installation",

    # Bearings (including white-metal)
    "white metal", "whitemetal", "babbitt", "bearing casting",
    "sleeve bearing", "bearing shells", "plummer block",

    # Fabrication / Workshop / Machining
    "machining", "fabrication", "steelwork", "welding", "turning", "milling",
    "line boring", "cnc", "workshop", "mechanical workshop", "refurbishment",

    # Repairs & Maintenance
    "maintenance", "mechanical maintenance", "repairs", "overhauls",
    "installation", "commissioning", "breakdown service",

    # Civil & Structural
    "pipework", "valves", "flanges", "civil works", "structural",
    "platform", "supports"
]

# ===========================================================
# SWITCHGEAR (Raise & Lower Integration)
# ===========================================================

SWITCHGEAR_KEYWORDS = [
    "switchgear", "mv switchgear", "lv switchgear", "distribution board",
    "db board", "panel upgrade", "electrical panel", "breaker", "circuit breaker",
    "vacuum breaker", "air circuit breaker", "isolator", "disconnect switch",
    "protection relay", "transformer panel", "mcc", "motor control centre",
    "enclosure", "control panel", "abb low voltage", "busbar", "electrical maintenance"
]

# ===========================================================
# CROSS CATEGORY (Triggers TES + Phakathi -> BOTH)
# ===========================================================

BOTH_CATEGORY_TRIGGERS = [
    "mechanical and chemical", "mechanical and water", "pump and water",
    "cooling and fabrication", "cooling tower refurbishment",
    "pump station upgrade", "boiler and mechanical",
    "chemical cleaning and mechanical repairs"
]

# ===========================================================
# OVERRIDE RULES (Hard logic)
# TES ALWAYS WINS if cooling/steam/chemistry is explicit
# PHAKATHI ALWAYS WINS if pump/mechanical supply is explicit
# BOTH is applied if scopes overlap significantly
# ===========================================================

TES_OVERRIDE = [
    "cooling", "steam", "boiler", "chemical", "water treatment",
    "condenser", "heat exchanger", "mexel"
]

PHAKATHI_OVERRIDE = [
    "pump", "bearing", "white metal", "machining", "fabrication",
    "switchgear", "mcc", "distribution board", "mechanical workshop"
]
