# ================================================
# KEYWORD RULES V2.0 - ACCURATE CAPABILITY MAPPING
# TES: Water treatment chemicals + dosing systems + monitoring
# Phakathi: NEW mechanical supply + white-metal bearing reconditioning ONLY
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
# TES KEYWORDS - Water Treatment Chemicals + Systems + Monitoring
# ===========================================================

TES_KEYWORDS = [
    # === 1. WATER TREATMENT CHEMICALS (Core Products) ===
    "water treatment chemicals", "chemical supply", "chemical dosing",
    
    # Scale Inhibitors
    "scale inhibitor", "antiscalant", "anti-scalant", "scale control",
    
    # Corrosion Inhibitors
    "corrosion inhibitor", "corrosion control", "corrosion barrier",
    
    # Biocides & Disinfectants
    "biocide", "biocidal", "antimicrobial", "microbiological control",
    "oxidizing biocide", "non-oxidizing biocide", "biological control",
    "chlorine", "chlorination", "chlorine dioxide", "hypochlorite",
    "calcium hypochlorite", "sodium hypochlorite", "bleach", "disinfectant",
    
    # Dispersants
    "dispersant", "fouling dispersant", "mud dispersant", "ash dispersant",
    
    # Film-Forming Agents (FFAs)
    "film forming amine", "ffa", "film forming agent", "film-forming",
    "mexsteam", "mexsteam 100", "steam treatment",
    
    # Surfactant-Based Conditioners
    "surfactant", "surfactant conditioner", "surfactant-based",
    "mexel", "mexel 432", "mexel432", "system conditioner",
    
    # Other Chemicals
    "oxygen scavenger", "passivation", "neutralising amine", "neutralizing amine",
    
    # === 2. COOLING TOWER TREATMENT ===
    "cooling tower", "cooling water treatment", "cooling tower treatment",
    "cooling tower chemicals", "cooling water chemicals", "cooling system",
    "condenser treatment", "cooling circuit", "cw treatment",
    "thermal efficiency", "fouling control", "fouling removal",
    
    # === 3. BOILER TREATMENT ===
    "boiler treatment", "boiler water treatment", "boiler chemicals",
    "feedwater treatment", "condensate treatment", "steam system",
    "boiler dosing", "steam quality", "boiler protection",
    
    # === 4. CHEMICAL DOSING SYSTEMS ===
    "chemical dosing system", "dosing system", "dosing skid",
    "dosing pump", "dosing equipment", "injection system",
    "chemical injection", "automated dosing", "dosing control",
    "tank and bund", "chemical storage",
    
    # === 5. WATER QUALITY MONITORING ===
    "water quality monitoring", "online monitoring", "water monitoring",
    "sensor", "ph probe", "conductivity", "orp", "redox",
    "corrosion probe", "monitoring system", "data intelligence",
    "compliance monitoring", "water analysis",
    
    # === 6. APPLICATIONS (Where TES works) ===
    "heat exchanger", "condenser", "evaporator", "chiller",
    "closed circuit", "open circuit", "recirculating system",
    "separation circuit", "mineral processing", "desalination",
]

# ===========================================================
# PHAKATHI KEYWORDS - NEW Mechanical Supply + White-Metal Bearing Reconditioning
# ===========================================================

PHAKATHI_KEYWORDS = [
    # === 1. NEW PUMP SUPPLY ===
    "supply of pumps", "supply and delivery of pumps", "pump supply",
    "new pumps", "pump procurement", "pumps tender",
    "centrifugal pump", "slurry pump", "dewatering pump",
    "vertical pump", "horizontal pump", "submersible pump",
    
    # === 2. NEW PUMP PARTS & COMPONENTS ===
    "pump spares", "pump parts", "pump components",
    "impeller supply", "impeller", "pump impeller",
    "mechanical seal", "seal supply", "pump seals",
    "shaft supply", "pump shaft", "wear rings", "wear parts",
    
    # === 3. NEW BEARING SUPPLY ===
    "bearing supply", "new bearings", "bearing procurement",
    "ball bearings", "roller bearings", "spherical bearings",
    "thrust bearings", "sleeve bearings", "journal bearings",
    
    # === 4. WHITE-METAL BEARING RECONDITIONING (ONLY EXCEPTION) ===
    "white metal bearing", "whitemetal bearing", "white-metal",
    "babbitt bearing", "white metal reconditioning", "bearing re-metalling",
    "white metal casting", "bearing reconditioning",
    "line boring", "bearing refurbishment",  # ONLY valid if "white metal" present
    "plummer block", "bearing shell",
    
    # === 5. FABRICATION WORKSHOP ===
    "fabrication services", "custom fabrication", "steel fabrication",
    "tank fabrication", "vessel fabrication", "structural fabrication",
    "laser profiling", "plasma profiling", "laser cutting",
    "rolling", "bending", "forming",
    
    # === 6. PRECISION MACHINING ===
    "machining services", "cnc machining", "precision machining",
    "turning", "milling", "boring", "grinding",
    "component manufacturing", "precision engineering",
    
    # === 7. CONVEYOR COMPONENTS (NEW) ===
    "conveyor components", "conveyor idler", "conveyor roller",
    "conveyor belting", "idler supply", "roller supply",
    "belt splice", "conveyor parts",
    
    # === 8. MECHANICAL COMPONENTS (NEW) ===
    "coupling", "flexible coupling", "gear coupling", "coupling adaptor",
    "gasket", "gland packing", "mechanical seal",
    "o-ring", "seal kit",
    "fittings", "fitting", "galvanised fitting", "pipe fitting",
    "adaptor", "washer",
    
    # === 9. HEAT TREATMENT ===
    "heat treatment", "stress relieving", "annealing",
    "normalizing", "hardening",
    
    # === 10. INDUSTRIAL TECHNOLOGY (IIoT & Controls) ===
    "instrumentation", "control system", "automation",
    "iiot", "industrial iot", "scada", "plc",
    "data analytics", "asset monitoring", "condition monitoring",
    "vibration monitoring", "predictive maintenance",
    
    # === 11. INSTALLATION (NEW equipment) ===
    "supply and installation", "supply and install",
    "installation services", "commissioning",
]

# ===========================================================
# SWITCHGEAR KEYWORDS - Electrical Panels & Control
# ===========================================================

SWITCHGEAR_KEYWORDS = [
    "switchgear supply", "mv switchgear", "lv switchgear",
    "distribution board supply", "db board supply",
    "panel supply", "control panel supply", "mcc supply",
    "motor control centre", "breaker supply",
]

# ===========================================================
# POSITIVE SIGNALS - If these appear, likely relevant
# ===========================================================

TES_STRONG_SIGNALS = [
    "cooling tower", "boiler", "water treatment", "chemical dosing",
    "scale inhibitor", "corrosion inhibitor", "biocide", "dispersant",
    "surfactant", "mexel", "mexel432", "film forming", "ffa",
    "dosing system", "water quality monitoring", "heat exchanger"
]

PHAKATHI_STRONG_SIGNALS = [
    "pump supply", "bearing supply", "white metal", "white-metal",
    "fabrication", "machining", "conveyor", "impeller",
    "laser profiling", "cnc machining", "bearing reconditioning"
]

# ===========================================================
# NEGATIVE SIGNALS - If these appear, likely NOT relevant
# ===========================================================

NEGATIVE_SIGNALS = [
    "maintenance", "refurbishment", "repair", "inspection",
    "transformer", "turbine", "spillage", "scrap", "disposal",
    "award", "cancellation", "regret", "bidders", "vehicle"
]

# ===========================================================
# OVERRIDE RULES & CROSS CATEGORY
# ===========================================================

TES_OVERRIDE = [
    "cooling tower", "boiler", "water treatment", "chemical dosing",
    "scale inhibitor", "corrosion inhibitor", "biocide", "dispersant",
    "surfactant", "mexel", "film forming", "dosing system",
    "water quality", "condenser treatment", "heat exchanger"
]

PHAKATHI_OVERRIDE = [
    "pump supply", "bearing supply", "white metal", "fabrication",
    "machining", "conveyor", "impeller", "laser profiling",
    "cnc", "precision machining", "component manufacturing"
]

BOTH_CATEGORY_TRIGGERS = [
    "pump station with water treatment", "cooling tower and pumps",
    "boiler and fabrication", "water treatment and mechanical"
]
