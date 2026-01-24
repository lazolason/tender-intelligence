import pytest
from classify_engine import classify_tender

@pytest.mark.parametrize("title,description,expected_category", [
    ("Power station cooling water treatment", "Supply of biocides and antiscalants", "MEXEL"),
    ("Office cleaning service", "Daily cleaning of municipal offices", "EXCLUDED"),
    ("CRAC unit maintenance", "Data center precision cooling services", "MEXEL"),
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
    assert "System ('cooling tower') + Action ('treatment') match" in result["reason"] or \
           "System ('boiler') + Action ('dosing') match" in result["reason"]
