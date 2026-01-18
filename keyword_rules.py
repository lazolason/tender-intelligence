# ================================================
# KEYWORD RULES V3.0 - MEXEL ENERGY SUSTAIN (TES)
# Sophisticated matching for Mexel-only tenders
# ================================================

# ===========================================================
# NEGATIVE KEYWORDS - Skip these tenders completely
# ===========================================================
NEGATIVE_KEYWORDS = [
    # ===== NEW NEGATIVES FROM BRAND GUIDELINES =====
    "swimming pool", "pool chemicals", "potable water bottling", "bottled water",
    "janitorial", "cleaning services", "laundry", "linen", "sewage removal",
    "lab reagents", "laboratory supplies", "household", "domestic",

    # ===== CONSTRUCTION / CIVIL =====
    "construction", "building construction", "civil construction", "civil works",
    "perimeter wall", "guardhouse", "guard house", "fencing", "palisade fence",
    "boundary wall", "security fence", "road construction", "building works",
    "structural", "civil inspection", "civil engineering",
    
    # ===== MAINTENANCE & REPAIR (ALL TYPES) =====
    "maintenance", "preventative maintenance", "planned maintenance",
    "routine maintenance", "mechanical maintenance", "electrical maintenance",
    "plant maintenance", "facility maintenance", "service and maintenance",
    "repair", "refurbishment", "overhaul", "inspection and maintenance",
    "service provider", "maintenance services", "repair services",
    
    # ===== REFURBISHMENT (EXCLUDE - except white-metal bearing reconditioning) =====
    "refurbishment", "refurbish", "overhaul", "retrofit",
    
    # ===== TRANSFORMERS & ELECTRICAL EQUIPMENT =====
    "transformer", "transformers", "transformer supply", "transformer oil",
    "aircells", "transformer aircells", "pressure relief devices",
    "power transformer", "distribution transformer", "voltage regulator",
    
    # ===== TURBINES =====
    "turbine", "turbines", "turbine pump", "turbine refurbishment",
    "turbine blades", "turbine overhaul", "gas turbine", "steam turbine",
    "turbine inspection", "turbine maintenance",
    
    # ===== METAL WORK / WELDING / COATING =====
    "metal spraying", "thermal spraying", "arc spraying", "flame spraying",
    "welding", "metallizing", "coating services", "galvanizing",
    
    # ===== INSPECTION SERVICES =====
    "inspection", "qci", "quality control inspectorate", "quality inspectorate",
    "inspection services", "tube solo", "solo inspection", "nde inspection",
    "non-destructive", "statutory inspection", "civil inspection",
    
    # ===== MEDICAL / SAFETY SERVICES =====
    "ambulance", "emergency response", "ert services", "medical services",
    "first aid", "occupational health",
    
    # ===== ENVIRONMENTAL / SPILLAGE =====
    "oil spillage", "spillage management", "environmental management",
    "hazardous spillage", "alien invasive species",
    
    # ===== SCRAP / DISPOSAL =====
    "scrap metal", "disposal", "scrap ferrous", "waste disposal",
    "ash dump", "dump extension",
    
    # ===== SECURITY =====
    "security guarding", "security guard", "physical security",
    "armed response", "access control", "cctv", "surveillance",
    
    # ===== CLEANING (EXTENDED) =====
    "cleaning services", "cleaning consumables", "janitorial",
    "office cleaning", "hygiene services",
    
    # ===== IT / ELECTRONICS =====
    "software", "it services", "computer", "laptop", "smart board",
    "smart meters", "network infrastructure", "website", "digital",
    
    # ===== VEHICLES / TRANSPORT =====
    "vehicle", "truck", "load bodies", "fleet", "transport services",
    "courier", "iveco", "trailers",
    
    # ===== PROFESSIONAL SERVICES =====
    "consulting", "professional services", "advisory", "recruitment",
    "training provider", "engineering services", "project management",
    "transaction advisory",
    
    # ===== FACILITIES / ADMIN =====
    "catering", "food supply", "canteen", "office renovation",
    "painting", "landscaping", "grass cutting", "property management",
    "minor works",
    
    # ===== TENDER ADMIN =====
    "notification of award", "award notification", "publication of bidders",
    "list of bidders", "regret letter", "tender cancellation",
    "tender validity", "names of bidders", "cancellation notification",
    
    # ===== ELECTRICAL SERVICES (too broad) =====
    "electrical services", "electrification", "electrical panel",
    "electrical infrastructure", "lv extension", "mv extension",
]

# ===========================================================
# STRONG MATCH KEYWORDS - High probability of Mexel (TES) fit
# ===========================================================
STRONG_MATCH_KEYWORDS = [
    "mexel", "mexel 432", "mexel432", "mexsteam", "mexsteam 100", "mexsteam100",
    "film forming amine", "filming amine", "film forming agent", "ffa",
    "scale inhibitor", "antiscalant", "anti-scalant", "corrosion inhibitor",
    "corrosion barrier", "oxygen scavenger", "oxidizing biocide",
    "non-oxidizing biocide", "neutralising amine", "neutralizing amine",
    "dispersant", "fouling dispersant", "mud dispersant", "ash dispersant",
    "biodispersant", "bio-dispersant", "cooling tower", "cooling water",
    "open recirculating", "closed loop cooling", "condenser cleaning",
    "condenser tubes", "boiler water treatment", "boiler chemical",
    "condensate treatment", "condensate polishing", "boiler blowdown",
    "deaerator", "legionella", "thermal efficiency", "heat transfer efficiency",
    "fouling factor", "approach temperature", "corrosion rate monitoring"
]

# ===========================================================
# WEAK MATCH KEYWORDS - Supporting signals
# ===========================================================
WEAK_MATCH_KEYWORDS = [
    "chemical supply", "chemical dosing", "surfactant", "surfactant-based",
    "system conditioner", "antimicrobial", "biological control",
    "microbiological control", "passivation", "membrane cleaning", "cip",
    "clean-in-place", "demineralisation", "demineralization", "ion exchange",
    "softener", "ro", "reverse osmosis"
]

# ===========================================================
# CONTEXT KEYWORDS - Areas where Mexel (TES) operates
# ===========================================================
CONTEXT_KEYWORDS = [
    "water", "treatment", "cooling", "boiler", "steam", "condensate",
    "tower", "heat exchanger", "condenser", "plant", "industrial",
    "utility", "power station", "refinery", "effluent", "process water"
]

# Aliases for backward compatibility
EXCLUDE_KEYWORDS = NEGATIVE_KEYWORDS
TES_KEYWORDS = STRONG_MATCH_KEYWORDS
TES_STRONG_SIGNALS = STRONG_MATCH_KEYWORDS