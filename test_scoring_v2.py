import json
from pathlib import Path


def _load_config():
    """Load optional local config, otherwise use safe built-in defaults."""
    config_path = Path(__file__).with_name("mexel_config.json")
    if config_path.exists():
        with config_path.open("r", encoding="utf-8") as f:
            return json.load(f)

    return {
        "keywords": {
            "exclusions": [
                "construction of", "civil works", "office furniture",
                "security service", "cleaning service", "water supply"
            ],
            "tier_1_strong": [
                "mexel", "mexel 432", "film forming amine",
                "thermal efficiency", "pue"
            ],
            "tier_2_weak": [
                "dosing", "treatment", "cooling tower", "boiler",
                "condenser", "crac", "crah"
            ],
            "tier_3_context": [
                "power station", "data center", "data centre",
                "industrial", "cooling"
            ],
        }
    }


config = _load_config()

def score_tender(title, description):
    """
    Returns a score and 'Match Type' (Gold, Potential, or Discard)
    """
    # Combine text for searching and normalize to lowercase
    full_text = f"{title} {description}".lower()
    
    # STEP 1: Check Exclusions (Hard Fail)
    for bad_word in config['keywords']['exclusions']:
        if bad_word in full_text:
            return 0, "DISCARD (Negative Keyword)"

    # STEP 2: Check Tier 1 (Strong Match)
    for word in config['keywords']['tier_1_strong']:
        if word in full_text:
            return 100, f"GOLD MATCH ({word})"

    # STEP 3: Check Tier 2 (Weak Match) + Tier 3 (Context)
    # We only count a Weak keyword if a Context keyword ALSO exists.
    has_weak = any(w in full_text for w in config['keywords']['tier_2_weak'])
    has_context = any(c in full_text for c in config['keywords']['tier_3_context'])

    if has_weak and has_context:
        return 80, "STRONG POTENTIAL (Context Validated)"
    
    # Fallback for broadly relevant terms without specific chemistry
    if has_context and "maintenance" in full_text:
        return 50, "REVIEW (General Maintenance)"

    return 0, "NO MATCH"

if __name__ == "__main__":
    # --- TEST BLOCK ---
    # Paste a fake SITA tender here to test
    test_title = "Refurbishment of HVAC and CRAC Units at SITA Centurion"
    test_desc = "Scope includes replacement of chilled water pumps and dosing systems."

    score, reason = score_tender(test_title, test_desc)
    print(f"Result: {score}/100 - {reason}")
