import re
from keyword_rules import STRONG_MATCH_KEYWORDS, SYSTEM_KEYWORDS, ACTION_KEYWORDS, NEGATIVE_KEYWORDS

def clean_text(text):
    """Normalize text for matching."""
    # Remove special chars but keep spaces
    text = re.sub(r'[^a-zA-Z0-9\s]', ' ', str(text))
    # Normalize whitespace
    text = re.sub(r'\s+', ' ', text)
    return text.lower().strip()

def has_any(text, keywords):
    """Check if any keyword exists in text. Returns the match or None."""
    for kw in keywords:
        # Simple inclusion check is usually sufficient and robust for phrases
        if kw in text:
            return kw
    return None

def classify_tender(title, description=""):
    """
    Classify tender based on Strict Profile logic.
    Returns: dict with 'category', 'reason', and 'short_title'
    """
    full_text = clean_text(f"{title} {description}")

    # 1. Check Exclusions
    neg_hit = has_any(full_text, NEGATIVE_KEYWORDS)
    if neg_hit:
        return {
            "category": "EXCLUDED",
            "reason": f"Negative keyword match: '{neg_hit}'",
            "short_title": title[:30]
        }

    # 2. Check Profile A (Product Match)
    strong_hit = has_any(full_text, STRONG_MATCH_KEYWORDS)
    if strong_hit:
        return {
            "category": "MEXEL",
            "reason": f"Strong Product match: '{strong_hit}'",
            "short_title": title[:30]
        }

    # 3. Check Profile B (System + Action Match)
    system_hit = has_any(full_text, SYSTEM_KEYWORDS)
    action_hit = has_any(full_text, ACTION_KEYWORDS)

    if system_hit and action_hit:
        return {
            "category": "MEXEL",
            "reason": f"System ('{system_hit}') + Action ('{action_hit}') match",
            "short_title": title[:30]
        }

    # Default
    return {
        "category": "EXCLUDED",
        "reason": "No competence profile match",
        "short_title": title[:30]
    }
