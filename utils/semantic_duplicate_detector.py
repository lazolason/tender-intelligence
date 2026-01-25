# ==========================================================
# SEMANTIC DUPLICATE DETECTOR - Advanced Deduplication
# Uses sentence embeddings to detect semantically similar tenders
# ==========================================================

import logging
from dataclasses import dataclass
from typing import Dict, Iterable, Optional, Tuple, List
from datetime import date

from utils.text_utils import normalize_text, parse_date, within_days

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticDuplicateMatch:
    """Result of semantic duplicate detection"""
    is_duplicate: bool
    similarity: float  # 0.0 to 1.0
    reason: str
    existing_ref: str
    existing_title: str
    existing_source: str
    match_type: str  # 'exact', 'fuzzy', 'semantic'


# Global model cache
_embedding_model = None


def _get_embedding_model():
    """
    Lazy load of sentence transformer model
    
    Returns:
        SentenceTransformer model instance
    """
    global _embedding_model
    
    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer
            # Use a fast, multilingual model
            _embedding_model = SentenceTransformer('all-MiniLM-L6-v2')
            logger.info("Loaded sentence transformer model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning("sentence-transformers not available, falling back to fuzzy matching")
            _embedding_model = None
        except Exception as e:
            logger.error(f"Failed to load embedding model: {e}")
            _embedding_model = None
    
    return _embedding_model



def _compute_embeddings(texts: List[str]) -> Optional[List]:
    """
    Compute embeddings for a list of texts
    
    Args:
        texts: List of text strings
        
    Returns:
        List of embeddings, or None if model unavailable
    """
    model = _get_embedding_model()
    if model is None:
        return None
    
    try:
        embeddings = model.encode(texts, show_progress_bar=False)
        return embeddings.tolist()
    except Exception as e:
        logger.error(f"Failed to compute embeddings: {e}")
        return None


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors
    
    Args:
        a: First vector
        b: Second vector
        
    Returns:
        Similarity score between 0.0 and 1.0
    """
    try:
        import numpy as np
        a_array = np.array(a)
        b_array = np.array(b)
        
        dot_product = np.dot(a_array, b_array)
        norm_a = np.linalg.norm(a_array)
        norm_b = np.linalg.norm(b_array)
        
        if norm_a == 0 or norm_b == 0:
            return 0.0
        
        return float(dot_product / (norm_a * norm_b))
    except ImportError:
        # Fallback to manual calculation
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(y ** 2 for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def _create_search_text(tender: Dict) -> str:
    """
    Create a searchable text representation of a tender
    
    Args:
        tender: Tender dictionary
        
    Returns:
        Combined text string for embedding
    """
    parts = []
    
    # Title (highest weight)
    title = tender.get("title", "")
    if title:
        parts.extend([title] * 3)  # Repeat for emphasis
    
    # Description
    description = tender.get("description", "")
    if description:
        parts.append(description)
    
    # Client
    client = tender.get("client", "")
    if client:
        parts.append(client)
    
    # Category
    category = tender.get("category", "")
    if category:
        parts.append(category)
    
    return " ".join(parts)




def find_semantic_duplicate(
    new_tender: Dict,
    existing_tenders: Iterable[Dict],
    *,
    semantic_threshold: float = 0.90,
    fuzzy_threshold: int = 85,
    date_window_days: int = 7,
    require_same_source: bool = True,
) -> Optional[SemanticDuplicateMatch]:
    """
    Find duplicate tenders using semantic similarity
    
    Args:
        new_tender: New tender to check
        existing_tenders: Iterable of existing tenders
        semantic_threshold: Cosine similarity threshold (0.0-1.0)
        fuzzy_threshold: Fuzzy string match threshold (0-100)
        date_window_days: Days to consider for date matching
        require_same_source: Whether to require same source
        
    Returns:
        SemanticDuplicateMatch object or None if no duplicate found
    """
    new_ref = (new_tender.get("ref") or "").strip().upper()
    new_title = (new_tender.get("title") or "").strip()
    new_source = (new_tender.get("source") or "Unknown").strip()
    new_closing = parse_date(new_tender.get("closing_date") or "")
    
    if not new_title:
        return None
    
    # Check exact ref match first (highest priority)
    for existing in existing_tenders:
        ex_ref = (existing.get("ref") or "").strip().upper()
        if new_ref and ex_ref and new_ref != "NA" and new_ref == ex_ref:
            return SemanticDuplicateMatch(
                is_duplicate=True,
                similarity=1.0,
                reason="Exact ref match",
                existing_ref=ex_ref,
                existing_title=existing.get("title", ""),
                existing_source=existing.get("source", ""),
                match_type="exact"
            )
    
    # Prepare texts for semantic comparison
    new_search_text = _create_search_text(new_tender)
    existing_search_texts = [_create_search_text(t) for t in existing_tenders]
    
    # Try semantic similarity first
    embeddings = _compute_embeddings([new_search_text] + existing_search_texts)
    
    if embeddings is not None:
        new_embedding = embeddings[0]
        existing_embeddings = embeddings[1:]
        
        for i, existing in enumerate(existing_tenders):
            ex_title = (existing.get("title") or "").strip()
            ex_source = (existing.get("source") or "Unknown").strip()
            ex_closing = parse_date(existing.get("closing_date") or "")
            
            # Check source requirement
            if require_same_source:
                new_source_norm = normalize_text(new_source)
                ex_source_norm = normalize_text(ex_source)
                if new_source_norm != ex_source_norm:
                    continue
            
            # Check date window
            same_source = normalize_text(new_source) == normalize_text(ex_source)
            close_date = within_days(new_closing, ex_closing, days=date_window_days)
            
            if same_source and not close_date and date_window_days > 0:
                # If dates don't match, don't consider duplicate
                continue
            
            # Calculate semantic similarity
            similarity = _cosine_similarity(new_embedding, existing_embeddings[i])
            
            if similarity >= semantic_threshold:
                return SemanticDuplicateMatch(
                    is_duplicate=True,
                    similarity=similarity,
                    reason=f"Semantic similarity ({similarity:.2f} >= {semantic_threshold})",
                    existing_ref=existing.get("ref", ""),
                    existing_title=ex_title,
                    existing_source=ex_source,
                    match_type="semantic"
                )
    
    # Fallback to fuzzy matching if semantic not available or no matches
    try:
        from fuzzywuzzy import fuzz as _fuzz
    except ImportError:
        _fuzz = None
    
    if _fuzz is not None:
        for existing in existing_tenders:
            ex_ref = (existing.get("ref") or "").strip().upper()
            ex_title = (existing.get("title") or "").strip()
            ex_source = (existing.get("source") or "Unknown").strip()
            ex_closing = parse_date(existing.get("closing_date") or "")
            
            # Skip if exact ref already checked
            if new_ref and ex_ref and new_ref != "NA" and new_ref == ex_ref:
                continue
            
            # Check source requirement
            if require_same_source:
                new_source_norm = normalize_text(new_source)
                ex_source_norm = normalize_text(ex_source)
                if new_source_norm != ex_source_norm:
                    continue
            
            # Check date window
            same_source = normalize_text(new_source) == normalize_text(ex_source)
            close_date = within_days(new_closing, ex_closing, days=date_window_days)
            
            if same_source and not close_date and date_window_days > 0:
                continue
            
            # Calculate fuzzy similarity
            similarity = _fuzz.ratio(new_title.lower(), ex_title.lower())
            if similarity >= fuzzy_threshold:
                return SemanticDuplicateMatch(
                    is_duplicate=True,
                    similarity=similarity / 100.0,  # Convert to 0-1 scale
                    reason=f"Fuzzy title match ({similarity}% >= {fuzzy_threshold}%)",
                    existing_ref=ex_ref,
                    existing_title=ex_title,
                    existing_source=ex_source,
                    match_type="fuzzy"
                )
    
    return None


def find_all_semantic_duplicates(
    tenders: List[Dict],
    *,
    semantic_threshold: float = 0.90,
    fuzzy_threshold: int = 85,
    date_window_days: int = 7,
    require_same_source: bool = True,
) -> List[Tuple[Dict, Dict, SemanticDuplicateMatch]]:
    """
    Find all duplicate pairs in a list of tenders
    
    Args:
        tenders: List of tender dictionaries
        semantic_threshold: Cosine similarity threshold
        fuzzy_threshold: Fuzzy string match threshold
        date_window_days: Days to consider for date matching
        require_same_source: Whether to require same source
        
    Returns:
        List of tuples (new_tender, existing_tender, match_info)
    """
    duplicates = []
    seen_refs = set()
    
    for i, tender in enumerate(tenders):
        # Compare with all previous tenders
        previous_tenders = tenders[:i]
        
        match = find_semantic_duplicate(
            tender,
            previous_tenders,
            semantic_threshold=semantic_threshold,
            fuzzy_threshold=fuzzy_threshold,
            date_window_days=date_window_days,
            require_same_source=require_same_source,
        )
        
        if match:
            # Find the matching existing tender
            existing_tender = None
            if match.existing_ref:
                for t in previous_tenders:
                    if t.get("ref") == match.existing_ref:
                        existing_tender = t
                        break
            duplicates.append((tender, existing_tender, match))
    
    return duplicates


def merge_duplicate_info(original: Dict, duplicate: Dict, match_info: SemanticDuplicateMatch) -> Dict:
    """
    Merge information from duplicate tender into original
    
    Args:
        original: Original tender dict
        duplicate: Duplicate tender dict
        match_info: Match information
        
    Returns:
        Enhanced original tender dict
    """
    # Add duplicate reference
    if 'duplicate_refs' not in original:
        original['duplicate_refs'] = []
    
    dup_ref = duplicate.get('ref', 'Unknown')
    if dup_ref not in original['duplicate_refs']:
        original['duplicate_refs'].append(dup_ref)
    
    # Merge descriptions if duplicate has more info
    orig_desc = original.get('description', '')
    dup_desc = duplicate.get('description', '')
    if len(dup_desc) > len(orig_desc):
        original['description'] = dup_desc
        original['description_enhanced'] = True
    
    # Merge URLs
    orig_url = original.get('url', '')
    dup_url = duplicate.get('url', '')
    if dup_url and dup_url != orig_url:
        if 'additional_urls' not in original:
            original['additional_urls'] = []
        if dup_url not in original['additional_urls']:
            original['additional_urls'].append(dup_url)
    
    # Add match info
    original['duplicate_match_info'] = {
        'similarity': match_info.similarity,
        'match_type': match_info.match_type,
        'reason': match_info.reason,
        'duplicate_source': match_info.existing_source
    }
    
    return original


def filter_duplicates(
    tenders: List[Dict],
    *,
    semantic_threshold: float = 0.90,
    fuzzy_threshold: int = 85,
    date_window_days: int = 7,
    require_same_source: bool = True,
    keep_first: bool = True,
) -> Tuple[List[Dict], List[Tuple[Dict, Dict, SemanticDuplicateMatch]]]:
    """
    Filter out duplicate tenders from a list
    
    Args:
        tenders: List of tender dictionaries
        semantic_threshold: Cosine similarity threshold
        fuzzy_threshold: Fuzzy string match threshold
        date_window_days: Days to consider for date matching
        require_same_source: Whether to require same source
        keep_first: If True, keep first occurrence, remove duplicates
        
    Returns:
        Tuple of (filtered_tenders, duplicate_matches)
    """
    if keep_first:
        # Process in order, keeping first occurrence
        filtered = []
        duplicates = []
        seen_refs = set()
        
        for tender in tenders:
            # Check against already filtered tenders
            match = find_semantic_duplicate(
                tender,
                filtered,
                semantic_threshold=semantic_threshold,
                fuzzy_threshold=fuzzy_threshold,
                date_window_days=date_window_days,
                require_same_source=require_same_source,
            )
            
            if match:
                # Merge duplicate info into original
                original = None
                if match.existing_ref:
                    matching_tenders = [t for t in filtered if t.get("ref") == match.existing_ref]
                    if matching_tenders:
                        original = matching_tenders[0]
                if original is not None:
                    original = merge_duplicate_info(original, tender, match)
                    duplicates.append((tender, original, match))
                else:
                    filtered.append(tender)
                    ref = tender.get('ref', '')
                    if ref:
                        seen_refs.add(ref)
            else:
                # No match found, this is a new tender
                filtered.append(tender)
                ref = tender.get('ref', '')
                if ref:
                    seen_refs.add(ref)
        
        return filtered, duplicates
    else:
        # Find all duplicate pairs
        all_duplicates = find_all_semantic_duplicates(
            tenders,
            semantic_threshold=semantic_threshold,
            fuzzy_threshold=fuzzy_threshold,
            date_window_days=date_window_days,
            require_same_source=require_same_source,
        )
        
        # Get refs to remove
        refs_to_remove = set()
        for _, _, match_info in all_duplicates:
            refs_to_remove.add(match_info.existing_ref)
        
        # Filter out duplicates
        filtered = [t for t in tenders if t.get('ref', '') not in refs_to_remove]
        
        return filtered, all_duplicates


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test with sample tenders
    test_tenders = [
        {
            "ref": "NT-001",
            "title": "Supply of water treatment chemicals",
            "description": "Supply and delivery of cooling water treatment chemicals",
            "source": "National Treasury",
            "closing_date": "2025-01-15"
        },
        {
            "ref": "NT-002",
            "title": "Provision of water treatment chemicals",
            "description": "Supply and delivery of cooling water treatment chemicals",
            "source": "National Treasury",
            "closing_date": "2025-01-15"
        },
        {
            "ref": "ESK-001",
            "title": "Pump supply for power station",
            "description": "Supply of centrifugal pumps",
            "source": "Eskom",
            "closing_date": "2025-01-20"
        },
    ]
    
    print("=" * 60)
    print("SEMANTIC DUPLICATE DETECTOR TEST")
    print("=" * 60)
    
    # Test finding duplicates
    for i in range(1, len(test_tenders)):
        print(f"\nChecking tender {i}: {test_tenders[i]['title']}")
        
        match = find_semantic_duplicate(
            test_tenders[i],
            test_tenders[:i],
            semantic_threshold=0.85,
            fuzzy_threshold=80
        )
        
        if match:
            print(f"  ✅ DUPLICATE FOUND:")
            print(f"     Type: {match.match_type}")
            print(f"     Similarity: {match.similarity:.2%}")
            print(f"     Reason: {match.reason}")
            print(f"     Existing: {match.existing_title} ({match.existing_ref})")
        else:
            print(f"  ❌ No duplicate found")
    
    # Test filtering
    print("\n" + "=" * 60)
    print("FILTERING TEST")
    print("=" * 60)
    
    filtered, duplicates = filter_duplicates(test_tenders, semantic_threshold=0.85)
    
    print(f"\nOriginal: {len(test_tenders)} tenders")
    print(f"Filtered: {len(filtered)} tenders")
    print(f"Duplicates found: {len(duplicates)}")
    
    print(f"\nFiltered tenders:")
    for t in filtered:
        print(f"  - {t['ref']}: {t['title']}")
