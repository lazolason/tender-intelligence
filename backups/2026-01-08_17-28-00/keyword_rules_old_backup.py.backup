# ================================================
# KEYWORD RULES FOR TENDER CLASSIFICATION ENGINE
# TES + Phakathi + Switchgear Logic (Locked)
# ================================================

# ===========================================================
# EXCLUSION LIST - Tenders to SKIP completely
# These are out of scope for TES & Phakathi
# ===========================================================

EXCLUDE_KEYWORDS = [
    # Construction / Civil
    "construction of", "building construction", "civil construction",
    "perimeter wall", "guardhouse", "guard house", "fencing",
    "palisade fence", "boundary wall", "security fence",
    "road construction", "building works",
    
    # Security Services
    "security guarding", "security guard", "physical security",
    "armed response", "access control", "cctv", "surveillance",
    "security services", "guarding services",
    
    # Cleaning / Consumables
    "cleaning services", "cleaning consumables", "janitorial",
    "office cleaning", "hygiene services",
    
    # IT / Software
    "software development", "it services", "computer", "laptop",
    "network infrastructure", "website",
    
    # Catering / Food
    "catering", "food supply", "canteen",
    
    # HR / Admin
    "recruitment", "staffing", "training provider",
    "consulting services", "professional services",
    
    # Vehicles / Transport
    "vehicle hire", "fleet management", "transport services",
    "courier services",
    
    # General Maintenance / Facilities (not water/chemical related)
    "repair of lights", "lighting", "light fittings",
    "aircon", "air conditioning", "air-condition", "air conditioner",
    "hvac maintenance",
    "painting", "plumbing repairs", "office renovation",
    "landscaping", "grass cutting", "garden services",
    
    # Equipment Maintenance & Refurbishment (OUT OF SCOPE)
    "maintenance services", "mechanical maintenance", "electrical maintenance",
    "preventative maintenance", "planned maintenance", "routine maintenance",
    "refurbishment", "overhaul", "repair services", "service and repair",
    "inspection and maintenance", "testing and maintenance",
    
    # Transformers & Electrical Supply (NOT what we do)
    "transformer", "transformers", "transformer supply", "transformer maintenance",
    "transformer aircells", "power transformer", "distribution transformer",
    "transformer oil", "voltage regulator",
    
    # Metal Work / Welding / Specialized Services (OUT OF SCOPE)
    "metal spraying", "thermal spraying", "arc spraying", "flame spraying",
    "welding services", "metallizing", "coating services",
    
    # Turbine Services (NOT our focus)
    "turbine maintenance", "turbine refurbishment", "turbine inspection",
    "turbine blades", "turbine overhaul", "gas turbine", "steam turbine",
    
    # General Electrical/Mechanical Services (too broad)
    "electrical services", "mechanical services", "engineering services",
    "industrial services", "plant maintenance", "facility maintenance",
]

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
    # Mechanical Supply & Rotating Equipment (SUPPLY/MANUFACTURING, not maintenance)
    "pump supply", "pump manufacturing", "impeller", "shaft", "mechanical seals",
    "gearbox supply", "couplings", "pump spares", "pump parts",
    "impeller casting", "pump installation", "new pumps",
    "bearing housings", "compensators", "bearing supply",
    "transmissions", "conveyor supply", "conveyor components", "idler supply",
    "roller supply", "belting", "gaskets supply", "gland packing",
    "static seals", "gearbox components",

    # Bearings (including white-metal) - SUPPLY/MANUFACTURING
    "white metal bearings", "whitemetal casting", "babbitt", "bearing casting",
    "sleeve bearing", "bearing shells", "plummer block",

    # Fabrication / Workshop / Machining (NEW PARTS, not repair)
    "machining services", "fabrication services", "custom fabrication",
    "manufacturing", "cnc machining",
    
    # NEW EQUIPMENT ONLY
    "pump procurement", "equipment supply", "pump tender", "bearing tender",
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
