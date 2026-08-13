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
    ("Boiler water treatment plant", "Maintenance of industrial utility", "PHAKATHI"),
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
    assert context_case["category"] == "PHAKATHI"
    assert "boiler water" in context_case.get("matched_keywords", [])

def test_should_exclude_backward_compatible_call():
    """Legacy callers passing only text + strong_hits should still work."""
    excluded, reason = should_exclude(clean("Construction of boundary wall"), [])
    assert excluded is True
    assert "construction of" in reason


@pytest.mark.parametrize(
    "title,description",
    [
        (
            "Bidders - Security Guarding Services for Peaking Operating Unit",
            "Security guarding services for Drakensberg Pumped Storage Scheme and power stations",
        ),
        (
            "SUPPLY AND DELIVERY OF LED LIGHT FIXTURES AT TUTUKA POWER STATION",
            "Supply and delivery of LED light fixtures at Tutuka Power Station once off",
        ),
        (
            "Tender Cancellation for C&I Refurbishment at Majuba Power Station",
            "Tender cancellation notice for refurbishment works at Majuba Power Station",
        ),
        (
            "Notification of Tender validity extension for supply and delivery of pipes and fittings",
            "Validity extension notice for supply and delivery at Majuba Power Station",
        ),
        (
            "Cancellation - Calibration, Service and ad hoc Maintenance of Chemical Services laboratory equipment",
            "Cancellation notice for laboratory equipment at Lethabo Power Station",
        ),
        (
            "Tender validity for Kendal Power Station Continuous Ash Disposal Facility",
            "Ground and surface water monitoring services at Kendal ash disposal facility",
        ),
        (
            "Piston Compressor Dewatering",
            "Services: General. Piston Compressor Dewatering",
        ),
        (
            "Alternative waste treatment facility",
            "Development of a municipal solid waste treatment facility",
        ),
        (
            "Approved professional person for power station ash dams",
            "Reference E1034GXMTL Bidders Names 2",
        ),
    ],
)
def test_classify_excludes_broad_site_plus_generic_action_false_positives(title, description):
    result = classify_tender(title, description)
    assert result["category"] == "EXCLUDED"


def test_classify_allows_specific_thermal_scope_at_power_station():
    result = classify_tender(
        "Arnot Power Station condenser performance restoration",
        "Cooling water treatment and efficiency restoration for the turbine condenser",
    )
    assert result["category"] == "MEXEL"
