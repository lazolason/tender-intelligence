
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender

def test_classification():
    test_cases = [
        {
            "title": "Supply of Mexel 432 oxidizing biocide",
            "description": "Chemical supply for water treatment",
            "expected_category": "MEXEL",
            "expected_keywords": ["mexel", "mexel 432", "oxidizing biocide"]
        },
        {
            "title": "Cooling tower water supply",
            "description": "Supply and delivery of chemical dosing equipment",
            "expected_category": "MEXEL",
            "expected_keywords": ["cooling tower", "chemical dosing"]
        },
        {
            "title": "Boiler water treatment plant",
            "description": "Maintenance of industrial utility",
            "expected_category": "MEXEL",
            "expected_keywords": ["boiler water treatment", "industrial", "utility", "plant"]
        },
        {
            "title": "Construction of boundary wall",
            "description": "Civil works for power station",
            "expected_category": "EXCLUDED",
            "expected_keywords": []
        },
        {
            "title": "Laundry services for hospital",
            "description": "Provision of linen cleaning",
            "expected_category": "EXCLUDED",
            "expected_keywords": []
        },
        {
            "title": "Boiler maintenance and repair",
            "description": "Routine service of steam plant",
            "expected_category": "EXCLUDED",
            "expected_keywords": []
        },
        {
            "title": "Supply of antiscalant for RO system",
            "description": "Reverse osmosis water treatment chemicals",
            "expected_category": "MEXEL",
            "expected_keywords": ["antiscalant", "ro", "reverse osmosis"]
        }
    ]

    print("=" * 60)
    print("CLASSIFICATION LOGIC TEST (V3.0)")
    print("=" * 60)

    passed = 0
    for i, tc in enumerate(test_cases):
        result = classify_tender(tc["title"], tc["description"])
        
        cat_match = result["category"] == tc["expected_category"]
        
        # Check if all expected keywords are present in matched_keywords
        matched = result.get("matched_keywords", [])
        keywords_ok = all(kw in matched for kw in tc["expected_keywords"]) if tc["expected_keywords"] else True
        
        status = "✅ PASS" if cat_match and keywords_ok else "❌ FAIL"
        if status == "✅ PASS":
            passed += 1
            
        print(f"\nTest {i+1}: {tc['title'][:50]}...")
        print(f"  Result: {result['category']} | Reason: {result['reason']}")
        print(f"  Matched: {matched}")
        print(f"  Status: {status}")
        
        if not cat_match:
            print(f"    ERROR: Expected category {tc['expected_category']}, got {result['category']}")
        if not keywords_ok:
            missing = [kw for kw in tc["expected_keywords"] if kw not in matched]
            print(f"    ERROR: Missing keywords: {missing}")

    print("\n" + "=" * 60)
    print(f"SUMMARY: {passed}/{len(test_cases)} tests passed")
    print("=" * 60)
    
    return passed == len(test_cases)

if __name__ == "__main__":
    success = test_classification()
    sys.exit(0 if success else 1)
