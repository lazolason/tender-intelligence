
import sys
import os
import time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender

def validate_transparency():
    test_cases = [
        {
            "name": "Exact Strong Match",
            "title": "Supply of Mexel 432 biocide",
            "description": "Looking for mexel 432 and scale inhibitor",
            "expected_category": "MEXEL",
            "expected_keywords": ["mexel", "mexel 432"]
        },
        {
            "name": "Context + Weak overlap",
            "title": "Water treatment chemical supply",
            "description": "Dosing of chemicals for plant utility",
            "expected_category": "EXCLUDED",
            "expected_keywords": []
        },
        {
            "name": "High Context overlap",
            "title": "Industrial boiler cooling tower",
            "description": "Steam plant process water systems",
            "expected_category": "EXCLUDED",
            "expected_keywords": []
        },
        {
            "name": "Excluded Tender - Construction",
            "title": "Construction of new office building",
            "description": "Civil works and building construction services",
            "expected_category": "EXCLUDED",
            "expected_keywords": [] # Should be empty for excluded
        },
        {
            "name": "Excluded Tender - Cleaning",
            "title": "Janitorial services for power station",
            "description": "Cleaning services and hygiene supplies",
            "expected_category": "EXCLUDED",
            "expected_keywords": [] # Should be empty for excluded
        },
        {
            "name": "Strong Signal Override Negative",
            "title": "Maintenance of Cooling Tower",
            "description": "Mexel 432 treatment and biocide dosing for cooling water",
            "expected_category": "MEXEL",
            "expected_keywords": ["mexel 432", "cooling tower", "cooling water"]
        }
    ]

    print("=" * 60)
    print("TRANSPARENCY VALIDATION 🔍")
    print("=" * 60)

    all_passed = True
    
    # 1. & 2. Accuracy and Empty Arrays for EXCLUDED
    for tc in test_cases:
        result = classify_tender(tc["title"], tc["description"])
        matched = result.get("matched_keywords", [])
        
        cat_ok = result["category"] == tc["expected_category"]
        keywords_ok = all(kw in matched for kw in tc["expected_keywords"])
        
        # Specific check: excluded tenders must have empty keywords
        if tc["expected_category"] == "EXCLUDED":
            if len(matched) > 0:
                keywords_ok = False
                print(f"  ❌ FAIL: {tc['name']} - Excluded tender should have empty keywords but found {matched}")

        status = "✅ PASS" if cat_ok and keywords_ok else "❌ FAIL"
        if status == "❌ FAIL": all_passed = False
        
        print(f"\n[{status}] {tc['name']}")
        print(f"  Result: {result['category']}")
        print(f"  Matched Keywords: {matched}")
        if not keywords_ok and tc["expected_category"] != "EXCLUDED":
            missing = [kw for kw in tc["expected_keywords"] if kw not in matched]
            print(f"  Missing: {missing}")

    # 3. Performance Check
    print("\n" + "=" * 60)
    print("PERFORMANCE BENCHMARK ⚡")
    print("=" * 60)
    
    iterations = 1000
    start_time = time.time()
    for _ in range(iterations):
        classify_tender("Supply of scale inhibitor for cooling water treatment", "Standard industrial boiler maintenance and chemical supply")
    end_time = time.time()
    
    total_ms = (end_time - start_time) * 1000
    avg_ms = total_ms / iterations
    
    print(f"Total time for {iterations} classifications: {total_ms:.2f}ms")
    print(f"Average time per classification: {avg_ms:.4f}ms")
    
    if avg_ms < 1.0:
        print("✅ PERFORMANCE OK: Classification is ultra-fast (< 1ms per tender)")
    else:
        print("⚠️ PERFORMANCE NOTE: Classification taking > 1ms. Monitor if tender volume grows significantly.")

    return all_passed

if __name__ == "__main__":
    success = validate_transparency()
    sys.exit(0 if success else 1)
