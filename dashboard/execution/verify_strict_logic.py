from classify_engine import classify_tender

tests = [
    ("Mexel 432 Supply", "Looking for supply of Mexel 432 chemicals", "MEXEL (Strong Match)"),
    ("Cooling Tower Cleaning", "Emergency cleaning of cooling towers", "MEXEL (System + Action)"),
    ("Boiler Maintenance", "General maintenance of boiler plant", "MEXEL (System + Action)"),
    ("Building Construction", "Construction of a new office building", "EXCLUDED (Negative)"),
    ("General Water Supply", "Supply of potable water to site", "EXCLUDED (No pairing)")
]

print("--- VERIFYING STRICT PAIRING LOGIC ---")
for title, desc, expected in tests:
    res = classify_tender(title, desc)
    print(f"TITLE: {title}")
    print(f"RESULT: {res['category']} ({res['reason']})")
    print("-" * 30)
