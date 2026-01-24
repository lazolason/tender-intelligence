from classify_engine import classify_tender

tests = [
    ("Boiler Maintenance", "Routine maintenance of steam boiler plant", "MEXEL (System+Action)"),
    ("Cooling Water Treatment", "Supply of chemicals for cooling water", "MEXEL (System+Action)"),
    ("Building Painting", "Painting of general office buildings", "EXCLUDED (No pairing)")
]

print("--- VERIFYING PHASE 2 STRICT COMPETENCE ---")
for title, desc, exp in tests:
    res = classify_tender(title, desc)
    print(f"TITLE: {title}")
    print(f"RESULT: {res['category']} | REASON: {res['reason']}")
    print("-" * 30)
