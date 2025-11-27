# ==========================================================
# TEXT CLEANER UTILITY
# Cleans and normalises text from scraped HTML
# ==========================================================

import re

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


def clean_filename(text: str) -> str:
    """
    Cleans text for use in filenames.
    Removes illegal characters.
    """
    if not text:
        return ""
    
    # Remove illegal filename characters
    text = re.sub(r'[<>:"/\\|?*]', "", text)
    
    # Replace spaces with underscores
    text = text.replace(" ", "_")
    
    # Remove multiple underscores
    text = re.sub(r"_+", "_", text)
    
    return text.strip("_")
