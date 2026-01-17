# ==========================================================
# TEXT CLEANER UTILITY
# Cleans and normalises text from scraped HTML
# ==========================================================

import re
from datetime import datetime

def clean_text(text: str) -> str:
    """
    Cleans raw text from HTML scraping.
    - Strips whitespace
    - Removes excessive newlines
    - Normalises spaces
    """
    if not text:
        return ""
    
    # Convert to string if needed
    text = str(text)
    
    # Remove newlines and tabs
    text = text.replace("\n", " ").replace("\t", " ").replace("\r", " ")
    
    # Remove multiple spaces
    text = re.sub(r"\s+", " ", text)
    
    # Strip leading/trailing whitespace
    text = text.strip()
    
    return text


def extract_closing_date_from_text(text: str):
    """Extract closing date from text"""
    date_pattern = r"(\d{1,2})\s*(January|February|March|April|May|June|July|August|September|October|November|December|Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)\s*(\d{4})?"
    
    match = re.search(date_pattern, text, re.I)
    if match:
        try:
            day = match.group(1)
            month = match.group(2)
            year = match.group(3) or str(datetime.now().year)
            return f"{year}-{month}-{day}"
        except:
            return None
    return None
