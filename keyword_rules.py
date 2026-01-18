# ================================================
# KEYWORD RULES V2.0 - MEXEL-ONLY MATCHING
# Mexel Energy Sustain (TES product) only
# ================================================

# ===========================================================
# EXCLUSION LIST - Skip these tenders completely
# ===========================================================

EXCLUDE_KEYWORDS = [
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
    # Note: "bearing reconditioning" is allowed ONLY if "white metal" is also present
    
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
    
    # ===== CLEANING =====
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
    
    # ===== TENDER ADMIN (notifications we don't care about) =====
    "notification of award", "award notification", "publication of bidders",
    "list of bidders", "regret letter", "tender cancellation",
    "tender validity", "names of bidders", "cancellation notification",
    
    # ===== ELECTRICAL SERVICES (too broad) =====
    "electrical services", "electrification", "electrical panel",
    "electrical infrastructure", "lv extension", "mv extension",
]

# ===========================================================
# TES KEYWORDS - Mexel brand + TES product references
# ===========================================================

TES_KEYWORDS = [
    "mexel",
    "mexel 432",
    "mexel432",
    "mexsteam",
    "mexsteam 100",
    "mexel energy sustain",
    "mexel energy",
    "tes",
]

# ===========================================================
# POSITIVE SIGNALS - If these appear, likely relevant
# ===========================================================

TES_STRONG_SIGNALS = [
    "mexel",
    "mexel 432",
    "mexel432",
    "mexsteam",
    "mexsteam 100",
    "mexel energy sustain",
    "mexel energy",
    "tes",
]
