# ==========================================================
# PDF TOOLS - File size and metadata detection
# ==========================================================

import urllib.request
from urllib.error import URLError


def get_pdf_size(url):
    """
    Get PDF file size from URL without downloading full file
    Returns human-readable size string or None if unavailable
    """
    if not url or not url.endswith('.pdf'):
        return None
    
    try:
        # Get headers without downloading body
        request = urllib.request.Request(url, method='HEAD')
        response = urllib.request.urlopen(request, timeout=5)
        
        size_bytes = int(response.headers.get('content-length', 0))
        if size_bytes == 0:
            return None
            
        return format_bytes(size_bytes)
    except (URLError, ValueError, TimeoutError):
        return None


def format_bytes(bytes_size):
    """Convert bytes to human-readable format"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if bytes_size < 1024.0:
            if unit == 'B':
                return f"{int(bytes_size)} {unit}"
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} TB"


def add_pdf_metadata(tender):
    """
    Add PDF size to tender dict if URL is PDF
    Returns modified tender dict
    """
    url = tender.get("url", "")
    if url.endswith('.pdf'):
        pdf_size = get_pdf_size(url)
        if pdf_size:
            tender["pdf_size"] = pdf_size
    return tender
