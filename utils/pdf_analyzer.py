# ==========================================================
# PDF ANALYZER - Enhanced PDF Content Extraction
# Extracts requirements, specifications, deadlines, and values from PDFs
# ==========================================================

import re
import requests
from datetime import datetime
from dateutil import parser as date_parser
from typing import Dict, List, Optional, Tuple
import os
import tempfile


def download_pdf(url: str, timeout: int = 30) -> Optional[bytes]:
    """
    Download PDF from URL to memory
    
    Args:
        url: PDF URL
        timeout: Request timeout in seconds
        
    Returns:
        PDF content as bytes, or None if download fails
    """
    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        response = requests.get(url, headers=headers, timeout=timeout, stream=True)
        response.raise_for_status()
        return response.content
    except Exception as e:
        print(f"   ⚠️ Failed to download PDF from {url}: {e}")
        return None


def extract_text_from_pdf(pdf_content: bytes) -> str:
    """
    Extract text from PDF content
    
    Args:
        pdf_content: PDF file content as bytes
        
    Returns:
        Extracted text as string
    """
    try:
        import pdfplumber
        with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp:
            tmp.write(pdf_content)
            tmp.close()
            
            text = ""
            with pdfplumber.open(tmp.name) as pdf:
                for page in pdf.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += page_text + "\n"
            
            os.unlink(tmp.name)
            return text
    except ImportError:
        # Fallback to PyPDF2 if pdfplumber not available
        try:
            import PyPDF2
            from io import BytesIO
            pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
            text = ""
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
            return text
        except Exception as e:
            print(f"   ⚠️ PDF text extraction failed: {e}")
            return ""
    except Exception as e:
        print(f"   ⚠️ PDF text extraction failed: {e}")
        return ""


def extract_sections(text: str, section_names: List[str]) -> Dict[str, str]:
    """
    Extract specific sections from tender document
    
    Args:
        text: Full document text
        section_names: List of section headings to extract
        
    Returns:
        Dictionary mapping section names to their content
    """
    sections = {}
    text_lower = text.lower()
    
    for section in section_names:
        section_lower = section.lower()
        # Find section start
        start_idx = text_lower.find(section_lower)
        if start_idx == -1:
            continue
        
        # Find next section (end of current section)
        end_idx = len(text)
        for other_section in section_names:
            if other_section.lower() == section_lower:
                continue
            other_idx = text_lower.find(other_section.lower(), start_idx + len(section))
            if other_idx != -1 and other_idx < end_idx:
                end_idx = other_idx
        
        # Extract section content
        section_text = text[start_idx:end_idx].strip()
        sections[section] = section_text[:2000]  # Limit to 2000 chars
    
    return sections


def extract_mandatory_requirements(text: str) -> List[str]:
    """
    Extract mandatory requirements from tender document
    
    Args:
        text: Document text
        
    Returns:
        List of mandatory requirement strings
    """
    requirements = []
    text_lower = text.lower()
    
    # Common patterns for mandatory requirements
    patterns = [
        r'mandatory\s*[:]\s*([^\n.]{10,200})',
        r'requirement\s*[:]\s*([^\n.]{10,200})',
        r'shall\s+([^\n.]{10,150})',
        r'must\s+([^\n.]{10,150})',
        r'compulsory\s*[:]\s*([^\n.]{10,200})',
        r'essential\s+([^\n.]{10,150})',
        r'cidb\s*rating\s*[:]\s*(\d+\s*[a-z]?)',
        r'bbbee\s*level\s*[:]\s*(\d+)',
        r'experience\s*[:]\s*(\d+\s*years?)',
        r'turnover\s*[:]\s*([^\n.]{10,100})',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, text_lower, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # Clean up the match
            req = match.strip()
            if len(req) > 20:  # Filter out short matches
                requirements.append(req[:200])
    
    # Remove duplicates while preserving order
    seen = set()
    unique_requirements = []
    for req in requirements:
        req_lower = req.lower()
        if req_lower not in seen:
            seen.add(req_lower)
            unique_requirements.append(req)
    
    return unique_requirements[:20]  # Limit to 20 requirements


def extract_deadlines(text: str) -> List[Dict[str, str]]:
    """
    Extract all dates from document
    
    Args:
        text: Document text
        
    Returns:
        List of dicts with date info
    """
    deadlines = []
    
    # Common date patterns in tenders
    date_patterns = [
        r'clos(?:ing|ed)\s*(?:date|time)?\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'closing\s*(?:date|time)?\s*[:]\s*(\d{1,2}\s+(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\s+\d{4})',
        r'deadline\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'submission\s*deadline\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'bid\s*closing\s*(?:date|time)?\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'site\s*visit\s*(?:date|time)?\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
        r'briefing\s*session\s*(?:date|time)?\s*[:]\s*(\d{1,2}[-/]\d{1,2}[-/]\d{2,4})',
    ]
    
    for pattern in date_patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            date_str = match.group(1)
            try:
                # Try to parse the date
                parsed_date = date_parser.parse(date_str, dayfirst=True, yearfirst=False)
                formatted_date = parsed_date.strftime("%Y-%m-%d")
                
                # Get context around the date
                start = max(0, match.start() - 50)
                end = min(len(text), match.end() + 50)
                context = text[start:end].replace('\n', ' ').strip()
                
                deadlines.append({
                    'date': formatted_date,
                    'raw': date_str,
                    'context': context
                })
            except:
                continue
    
    # Remove duplicates
    seen = set()
    unique_deadlines = []
    for deadline in deadlines:
        if deadline['date'] not in seen:
            seen.add(deadline['date'])
            unique_deadlines.append(deadline)
    
    return unique_deadlines


def extract_monetary_values(text: str) -> List[Dict[str, any]]:
    """
    Extract monetary values from document
    
    Args:
        text: Document text
        
    Returns:
        List of dicts with value info
    """
    values = []
    
    # Currency patterns
    patterns = [
        r'(?:r|rand)\s*(\d+(?:[,.]\d{3})*(?:\s*million|m)?)',
        r'(?:r|rand)\s*(\d+(?:[,.]\d{3})*(?:\s*thousand|k)?)',
        r'zar?\s*(\d+(?:[,.]\d{3})*(?:\s*million|m)?)',
        r'zar?\s*(\d+(?:[,.]\d{3})*(?:\s*thousand|k)?)',
        r'us\s*\$\s*(\d+(?:[,.]\d{3})*)',
        r'\$\s*(\d+(?:[,.]\d{3})*)',
    ]
    
    for pattern in patterns:
        matches = re.finditer(pattern, text, re.IGNORECASE)
        for match in matches:
            value_str = match.group(1)
            
            # Parse numeric value
            value_str_clean = value_str.replace(',', '').replace('.', '')
            try:
                value = float(value_str_clean)
                
                # Determine scale
                context = text[max(0, match.start() - 30):match.end() + 30]
                scale = 1
                if 'million' in context.lower() or 'm' in context.lower():
                    scale = 1000000
                elif 'thousand' in context.lower() or 'k' in context.lower():
                    scale = 1000
                
                actual_value = value * scale
                
                values.append({
                    'value': actual_value,
                    'formatted': f"R{actual_value:,.0f}",
                    'context': context.replace('\n', ' ').strip()
                })
            except:
                continue
    
    # Remove duplicates and sort by value
    seen = set()
    unique_values = []
    for val in values:
        val_key = f"{val['value']}:{val['context'][:50]}"
        if val_key not in seen:
            seen.add(val_key)
            unique_values.append(val)
    
    unique_values.sort(key=lambda x: x['value'], reverse=True)
    return unique_values[:10]  # Limit to 10 values


def extract_contact_info(text: str) -> Dict[str, str]:
    """
    Extract contact information from document
    
    Args:
        text: Document text
        
    Returns:
        Dict with contact details
    """
    contact = {}
    
    # Email patterns
    email_pattern = r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}'
    emails = re.findall(email_pattern, text)
    if emails:
        contact['email'] = emails[0]
    
    # Phone patterns (South African format)
    phone_patterns = [
        r'(\+27\s*\d{2,3}\s*\d{3}\s*\d{4})',
        r'(0\d{2}\s*\d{3}\s*\d{4})',
        r'(\d{3}\s*\d{3}\s*\d{4})',
    ]
    for pattern in phone_patterns:
        phones = re.findall(pattern, text)
        if phones:
            contact['phone'] = phones[0]
            break
    
    # Person name patterns
    name_patterns = [
        r'contact\s*person\s*[:]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'enquiries\s*[:]\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
        r'for\s+enquiries\s+contact\s*([A-Z][a-z]+\s+[A-Z][a-z]+)',
    ]
    for pattern in name_patterns:
        names = re.findall(pattern, text, re.IGNORECASE)
        if names:
            contact['name'] = names[0]
            break
    
    return contact


def analyze_pdf(url: str) -> Dict[str, any]:
    """
    Main function to analyze a tender PDF
    
    Args:
        url: PDF URL
        
    Returns:
        Dictionary with all extracted information
    """
    result = {
        'url': url,
        'success': False,
        'text': '',
        'sections': {},
        'requirements': [],
        'deadlines': [],
        'values': [],
        'contact': {},
        'word_count': 0,
        'page_count': 0
    }
    
    # Download PDF
    pdf_content = download_pdf(url)
    if not pdf_content:
        return result
    
    # Extract text
    text = extract_text_from_pdf(pdf_content)
    if not text:
        return result
    
    result['success'] = True
    result['text'] = text
    result['word_count'] = len(text.split())
    
    # Try to get page count
    try:
        import PyPDF2
        from io import BytesIO
        pdf_reader = PyPDF2.PdfReader(BytesIO(pdf_content))
        result['page_count'] = len(pdf_reader.pages)
    except:
        pass
    
    # Extract sections
    section_names = [
        'Technical Specifications',
        'Technical Specs',
        'Specifications',
        'Scope of Work',
        'Scope',
        'Requirements',
        'Mandatory Requirements',
        'Evaluation Criteria',
        'Terms and Conditions',
        'Instructions to Bidders',
        'Submission Requirements'
    ]
    result['sections'] = extract_sections(text, section_names)
    
    # Extract requirements
    result['requirements'] = extract_mandatory_requirements(text)
    
    # Extract deadlines
    result['deadlines'] = extract_deadlines(text)
    
    # Extract monetary values
    result['values'] = extract_monetary_values(text)
    
    # Extract contact info
    result['contact'] = extract_contact_info(text)
    
    return result


def add_pdf_analysis_to_tender(tender: Dict[str, any]) -> Dict[str, any]:
    """
    Add PDF analysis results to tender dict
    
    Args:
        tender: Tender dictionary
        
    Returns:
        Enhanced tender dictionary with PDF analysis
    """
    url = tender.get('url', '')
    
    # Only analyze PDFs
    if not url.endswith('.pdf'):
        return tender
    
    print(f"   📄 Analyzing PDF: {url}")
    
    analysis = analyze_pdf(url)
    
    if analysis['success']:
        # Add analysis results to tender
        tender['pdf_analysis'] = {
            'page_count': analysis['page_count'],
            'word_count': analysis['word_count'],
            'requirements_count': len(analysis['requirements']),
            'deadlines_count': len(analysis['deadlines']),
            'values_count': len(analysis['values'])
        }
        
        # Add sections if found
        if analysis['sections']:
            tender['pdf_sections'] = analysis['sections']
        
        # Add requirements if found
        if analysis['requirements']:
            tender['pdf_requirements'] = analysis['requirements']
        
        # Add deadlines if found
        if analysis['deadlines']:
            tender['pdf_deadlines'] = analysis['deadlines']
        
        # Add values if found
        if analysis['values']:
            tender['pdf_values'] = analysis['values']
        
        # Add contact if found
        if analysis['contact']:
            tender['pdf_contact'] = analysis['contact']
        
        print(f"      ✅ Extracted: {len(analysis['requirements'])} requirements, "
              f"{len(analysis['deadlines'])} deadlines, "
              f"{len(analysis['values'])} values")
    else:
        print(f"      ⚠️ PDF analysis failed")
    
    return tender


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test with a sample URL (replace with actual tender PDF URL)
    test_url = "https://www.etenders.gov.za/content/sample.pdf"
    
    print("=" * 60)
    print("PDF ANALYZER TEST")
    print("=" * 60)
    
    result = analyze_pdf(test_url)
    
    print(f"\nSuccess: {result['success']}")
    print(f"Word count: {result['word_count']}")
    print(f"Page count: {result['page_count']}")
    
    print(f"\nSections found: {len(result['sections'])}")
    for section, content in result['sections'].items():
        print(f"  - {section}: {content[:100]}...")
    
    print(f"\nRequirements: {len(result['requirements'])}")
    for req in result['requirements'][:5]:
        print(f"  - {req}")
    
    print(f"\nDeadlines: {len(result['deadlines'])}")
    for deadline in result['deadlines']:
        print(f"  - {deadline['date']}: {deadline['context'][:80]}")
    
    print(f"\nValues: {len(result['values'])}")
    for val in result['values'][:5]:
        print(f"  - {val['formatted']}: {val['context'][:80]}")
    
    print(f"\nContact: {result['contact']}")
