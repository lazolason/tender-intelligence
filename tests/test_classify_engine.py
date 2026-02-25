import pytest
from classify_engine import classify_tender, should_exclude, clean

@pytest.mark.parametrize("title,description,expected_category", [
    ("Power station cooling water treatment", "Supply of biocides and antiscalants", "MEXEL"),
    ("Supply of oxidizing biocide", "Chemical supply for water treatment", "MEXEL"),
    ("Supply of antiscalant for RO system", "Reverse osmosis water treatment chemicals", "MEXEL"),
    ("Cooling tower water supply", "Supply and delivery of chemical dosing equipment", "MEXEL"),
    ("Office cleaning service", "Daily cleaning of municipal offices", "EXCLUDED"),
    ("CRAC unit maintenance", "Data center precision cooling services", "MEXEL"),
    ("Boiler maintenance and repair", "Routine service of steam plant", "EXCLUDED"),
    ("Supply of laptops", "High performance computers for staff", "EXCLUDED"),
    ("Mexel 432 delivery", "3 tons of film forming amine", "MEXEL"),
])
def test_classify_full_pipeline(title, description, expected_category):
    result = classify_tender(title, description)
    assert result["category"] == expected_category
    assert "reason" in result
    assert "short_title" in result

def test_classify_normalization():
    """Verify that text normalization works correctly."""
    # Special characters should be removed/normalized
    title = "Cooling-Tower: Treatment!!"
    description = "Boiler....Dosing"
    
    result = classify_tender(title, description)
    assert result["category"] == "MEXEL"
    assert "Competence Match (Profile B): cooling tower + treatment" in result["reason"] or \
           "Competence Match (Profile B): cooling tower + dosing" in result["reason"] or \
           "Competence Match (Profile B): boiler + dosing" in result["reason"]

def test_hyphenated_system_keyword_normalization():
    """Hyphenated system phrases should match the same as spaced phrases."""
    spaced = classify_tender("Cooling Tower Treatment", "chemical service")
    hyphen = classify_tender("Cooling-Tower Treatment", "chemical service")
    assert spaced["category"] == "MEXEL"
    assert hyphen["category"] == "MEXEL"

def test_classify_keyword_aliases():
    """Verify matched keyword aliases for reporting/debug output."""
    ro_case = classify_tender("Supply of antiscalant for RO system", "Reverse osmosis water treatment chemicals")
    assert ro_case["category"] == "MEXEL"
    assert "ro" in ro_case.get("matched_keywords", [])

    dosing_case = classify_tender("Cooling tower water supply", "Supply and delivery of chemical dosing equipment")
    assert dosing_case["category"] == "MEXEL"
    assert "chemical dosing" in dosing_case.get("matched_keywords", [])

    context_case = classify_tender("Boiler water treatment plant", "Maintenance of industrial utility")
    assert context_case["category"] == "MEXEL"
    assert "industrial" in context_case.get("matched_keywords", [])
    assert "utility" in context_case.get("matched_keywords", [])
    assert "plant" in context_case.get("matched_keywords", [])

def test_should_exclude_backward_compatible_call():
    """Legacy callers passing only text + strong_hits should still work."""
    excluded, reason = should_exclude(clean("Construction of boundary wall"), [])
    assert excluded is True
    assert "construction of" in reason
