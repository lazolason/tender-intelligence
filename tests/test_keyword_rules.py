import pytest
from keyword_rules import STRONG_MATCH_KEYWORDS, SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS, EXCLUDE_KEYWORDS

def has_any(text, keywords):
    """Utility to check if any keyword appears in text (case-insensitive)."""
    text_lower = text.lower()
    return any(kw.lower() in text_lower for kw in keywords)

def classify_logic(text):
    """Simplified version of the classification logic for testing."""
    text_lower = text.lower()
    
    # 1. NEGATIVE match → EXCLUDE (overrides all)
    neg_matches = [kw for kw in NEGATIVE_KEYWORDS if kw.lower() in text_lower]
    if neg_matches:
        return "EXCLUDE", f"Negative match: {neg_matches}"
        
    # 2. STRONG_MATCH → INCLUDE
    strong_matches = [kw for kw in STRONG_MATCH_KEYWORDS if kw.lower() in text_lower]
    if strong_matches:
        return "INCLUDE", f"Strong match: {strong_matches}"
        
    # 3. (SYSTEM + ACTION) → INCLUDE
    system_matches = [kw for kw in SYSTEM_KEYWORDS if kw.lower() in text_lower]
    action_matches = [kw for kw in ACTION_KEYWORDS if kw.lower() in text_lower]
    if system_matches and action_matches:
        return "INCLUDE", f"System: {system_matches}, Action: {action_matches}"
        
    return "EXCLUDE", "No match"

@pytest.mark.parametrize("text,expected_result", [
    # STRONG MATCH tests
    ("Mexel 432 treatment", "INCLUDE"),
    ("Legionella control services", "INCLUDE"),
    ("Asme ptc 12.2 performance test", "INCLUDE"),
    ("Surfactant supply for cooling", "INCLUDE"),
    
    # SYSTEM + ACTION tests (MEXEL scope: cooling water, condensers, thermal efficiency)
    ("Cooling tower treatment", "INCLUDE"),
    # Note: "Boiler chemical dosing" now routes to PHAKATHI (boiler chemistry scope),
    # not detectable via simplified SYSTEM+ACTION logic here — covered in test_classify_engine.py
    ("Condenser efficiency optimization", "INCLUDE"),
    ("CRAC unit water treatment", "INCLUDE"),
    ("Data center precision cooling maintenance", "INCLUDE"),
    ("Server room thermal efficiency", "INCLUDE"),
    
    # NEGATIVE MATCH tests (Specific building HVAC)
    ("Office air conditioning split unit", "EXCLUDE"),
    ("Building hvac maintenance", "EXCLUDE"),
    ("Building air conditioning repair", "EXCLUDE"),
    ("General ventilation system", "EXCLUDE"),
    
    # MIXED tests (Negative should win)
    ("Data center crac unit and office split unit", "EXCLUDE"),
    ("Mexel 432 for building hvac", "EXCLUDE"),
    
    # NO MATCH tests
    ("Security guard services", "EXCLUDE"),
    ("Supply of office furniture", "EXCLUDE"),
    ("Cleaning of office windows", "EXCLUDE"), # "cleaning" is an action but no system
])
def test_classification_logic(text, expected_result):
    result, reason = classify_logic(text)
    assert result == expected_result, f"Failed for '{text}': {reason}"

def test_hvac_removal_rationale():
    """Verify that 'hvac' itself is NOT a negative keyword anymore."""
    assert "hvac" not in [kw.lower() for kw in NEGATIVE_KEYWORDS]
    
    # But specific building HVAC terms are
    assert "building hvac" in [kw.lower() for kw in NEGATIVE_KEYWORDS]
    assert "office air conditioning" in [kw.lower() for kw in NEGATIVE_KEYWORDS]
    assert "split unit" in [kw.lower() for kw in NEGATIVE_KEYWORDS]

def test_data_center_keywords_present():
    """Verify that the new data center keywords are in the correct profiles."""
    strong = [kw.lower() for kw in STRONG_MATCH_KEYWORDS]
    # Systems
    systems = [kw.lower() for kw in SYSTEM_KEYWORDS]
    assert "crac" in systems
    assert "crah" in systems
    assert "data center" in systems
    assert "precision cooling" in systems
    
    # Strong matches
    assert "pue" in strong
    assert "condenser efficiency" in strong

    # Actions
    actions = [kw.lower() for kw in ACTION_KEYWORDS]
    assert "thermal efficiency" in actions

def test_legacy_exclude_keywords_alias():
    """Legacy imports should still resolve to the negative keyword list."""
    assert EXCLUDE_KEYWORDS is NEGATIVE_KEYWORDS


@pytest.mark.parametrize(
    "keyword_list",
    [STRONG_MATCH_KEYWORDS, SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS],
)
def test_keyword_lists_do_not_contain_exact_duplicates(keyword_list):
    """Keyword lists should stay deduplicated for maintainability."""
    assert len(keyword_list) == len(set(keyword_list))
