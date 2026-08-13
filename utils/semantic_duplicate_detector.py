# ==========================================================
# SEMANTIC DUPLICATE DETECTOR - Advanced Deduplication
# Uses sentence embeddings to detect semantically similar tenders
# ==========================================================

import logging
from dataclasses import dataclass, field
from time import perf_counter
from typing import Dict, Iterable, List, Optional, Tuple

from utils.text_utils import normalize_text, parse_date, within_days


logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class SemanticDuplicateMatch:
    """Result of semantic duplicate detection."""

    is_duplicate: bool
    similarity: float  # 0.0 to 1.0
    reason: str
    existing_ref: str
    existing_title: str
    existing_source: str
    match_type: str  # 'exact', 'fuzzy', 'semantic'


@dataclass
class IndexedTender:
    """Precomputed comparison data for one tender."""

    tender: Dict
    ref: str
    title: str
    source: str
    source_norm: str
    closing_date: Optional[object]
    search_text: str
    embedding: Optional[List[float]] = None


@dataclass
class SemanticTenderIndex:
    """Reusable semantic comparison index for a tender collection."""

    entries: List[IndexedTender] = field(default_factory=list)
    ref_map: Dict[str, IndexedTender] = field(default_factory=dict)

    def add_tender(self, tender: Dict) -> None:
        entry = _build_index_entry(tender)
        embeddings = _compute_embeddings([entry.search_text])
        if embeddings is not None:
            entry.embedding = embeddings[0]
        self.entries.append(entry)
        if entry.ref:
            self.ref_map[entry.ref] = entry


# Global model cache
_embedding_model = None
_embedding_cache: Dict[str, List[float]] = {}


def _get_embedding_model():
    """
    Lazy load the sentence transformer model.

    Returns:
        SentenceTransformer model instance
    """
    global _embedding_model

    if _embedding_model is None:
        try:
            from sentence_transformers import SentenceTransformer

            _embedding_model = SentenceTransformer("all-MiniLM-L6-v2")
            logger.info("Loaded sentence transformer model: all-MiniLM-L6-v2")
        except ImportError:
            logger.warning(
                "sentence-transformers not available, falling back to fuzzy matching"
            )
            _embedding_model = None
        except Exception as exc:
            logger.error("Failed to load embedding model: %s", exc)
            _embedding_model = None

    return _embedding_model


def _compute_embeddings(texts: List[str]) -> Optional[List[List[float]]]:
    """
    Compute embeddings for a list of texts, reusing in-process cache entries.

    Args:
        texts: List of text strings

    Returns:
        List of embeddings, or None if the model is unavailable
    """
    if not texts:
        return []

    model = _get_embedding_model()
    if model is None:
        return None

    missing_texts = [text for text in dict.fromkeys(texts) if text not in _embedding_cache]

    if missing_texts:
        try:
            started = perf_counter()
            encoded = model.encode(missing_texts, show_progress_bar=False)
            for text, embedding in zip(missing_texts, encoded):
                _embedding_cache[text] = (
                    embedding.tolist() if hasattr(embedding, "tolist") else list(embedding)
                )
            logger.debug(
                "Computed %s new semantic embeddings in %.2fs",
                len(missing_texts),
                perf_counter() - started,
            )
        except Exception as exc:
            logger.error("Failed to compute embeddings: %s", exc)
            return None

    return [_embedding_cache[text] for text in texts]


def _cosine_similarity(a: List[float], b: List[float]) -> float:
    """
    Calculate cosine similarity between two vectors.

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
        dot = sum(x * y for x, y in zip(a, b))
        norm_a = sum(x ** 2 for x in a) ** 0.5
        norm_b = sum(y ** 2 for y in b) ** 0.5
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)


def _create_search_text(tender: Dict) -> str:
    """
    Create a searchable text representation of a tender.

    Args:
        tender: Tender dictionary

    Returns:
        Combined text string for embedding
    """
    parts = []

    title = tender.get("title", "")
    if title:
        parts.extend([title] * 3)

    description = tender.get("description", "")
    if description:
        parts.append(description)

    client = tender.get("client", "")
    if client:
        parts.append(client)

    category = tender.get("category", "")
    if category:
        parts.append(category)

    return " ".join(parts)


def _build_index_entry(
    tender: Dict,
    *,
    search_text: Optional[str] = None,
    embedding: Optional[List[float]] = None,
) -> IndexedTender:
    title = (tender.get("title") or "").strip()
    source = (tender.get("source") or "Unknown").strip()
    return IndexedTender(
        tender=tender,
        ref=(tender.get("ref") or "").strip().upper(),
        title=title,
        source=source,
        source_norm=normalize_text(source),
        closing_date=parse_date(tender.get("closing_date") or ""),
        search_text=search_text if search_text is not None else _create_search_text(tender),
        embedding=embedding,
    )


def build_semantic_index(tenders: Iterable[Dict]) -> SemanticTenderIndex:
    """
    Build a reusable semantic comparison index for a tender collection.
    """
    tender_list = list(tenders)
    index = SemanticTenderIndex()
    if not tender_list:
        return index

    search_texts = [_create_search_text(tender) for tender in tender_list]
    embeddings = _compute_embeddings(search_texts)

    for i, tender in enumerate(tender_list):
        embedding = embeddings[i] if embeddings is not None else None
        entry = _build_index_entry(
            tender,
            search_text=search_texts[i],
            embedding=embedding,
        )
        index.entries.append(entry)
        if entry.ref:
            index.ref_map[entry.ref] = entry

    return index


def find_semantic_duplicate(
    new_tender: Dict,
    existing_tenders: Optional[Iterable[Dict]] = None,
    *,
    existing_index: Optional[SemanticTenderIndex] = None,
    semantic_threshold: float = 0.90,
    fuzzy_threshold: int = 85,
    date_window_days: int = 7,
    require_same_source: bool = True,
) -> Optional[SemanticDuplicateMatch]:
    """
    Find duplicate tenders using semantic similarity.

    Args:
        new_tender: New tender to check
        existing_tenders: Iterable of existing tenders
        existing_index: Optional precomputed index for existing tenders
        semantic_threshold: Cosine similarity threshold (0.0-1.0)
        fuzzy_threshold: Fuzzy string match threshold (0-100)
        date_window_days: Days to consider for date matching
        require_same_source: Whether to require same source

    Returns:
        SemanticDuplicateMatch object or None if no duplicate found
    """
    if existing_index is None:
        existing_index = build_semantic_index(existing_tenders or [])

    new_ref = (new_tender.get("ref") or "").strip().upper()
    new_title = (new_tender.get("title") or "").strip()
    new_source = (new_tender.get("source") or "Unknown").strip()
    new_source_norm = normalize_text(new_source)
    new_closing = parse_date(new_tender.get("closing_date") or "")

    if not new_title:
        return None

    if new_ref and new_ref != "NA" and new_ref in existing_index.ref_map:
        existing = existing_index.ref_map[new_ref]
        return SemanticDuplicateMatch(
            is_duplicate=True,
            similarity=1.0,
            reason="Exact ref match",
            existing_ref=existing.ref,
            existing_title=existing.title,
            existing_source=existing.source,
            match_type="exact",
        )

    def has_distinct_authoritative_ref(entry: IndexedTender) -> bool:
        return bool(
            new_tender.get("ref_is_authoritative")
            and entry.tender.get("ref_is_authoritative")
            and new_ref
            and new_ref != "NA"
            and entry.ref
            and new_ref != entry.ref
        )

    new_search_text = _create_search_text(new_tender)
    new_embeddings = _compute_embeddings([new_search_text])
    new_embedding = new_embeddings[0] if new_embeddings else None

    if new_embedding is not None:
        for entry in existing_index.entries:
            if require_same_source and new_source_norm != entry.source_norm:
                continue
            if has_distinct_authoritative_ref(entry):
                continue

            same_source = new_source_norm == entry.source_norm
            close_date = within_days(new_closing, entry.closing_date, days=date_window_days)
            if same_source and not close_date and date_window_days > 0:
                continue

            if not entry.embedding:
                continue

            similarity = _cosine_similarity(new_embedding, entry.embedding)
            if similarity >= semantic_threshold:
                return SemanticDuplicateMatch(
                    is_duplicate=True,
                    similarity=similarity,
                    reason=f"Semantic similarity ({similarity:.2f} >= {semantic_threshold})",
                    existing_ref=entry.ref,
                    existing_title=entry.title,
                    existing_source=entry.source,
                    match_type="semantic",
                )

    try:
        from fuzzywuzzy import fuzz as _fuzz
    except ImportError:
        _fuzz = None

    if _fuzz is not None:
        for entry in existing_index.entries:
            if new_ref and entry.ref and new_ref != "NA" and new_ref == entry.ref:
                continue

            if require_same_source and new_source_norm != entry.source_norm:
                continue
            if has_distinct_authoritative_ref(entry):
                continue

            same_source = new_source_norm == entry.source_norm
            close_date = within_days(new_closing, entry.closing_date, days=date_window_days)
            if same_source and not close_date and date_window_days > 0:
                continue

            similarity = _fuzz.ratio(new_title.lower(), entry.title.lower())
            if similarity >= fuzzy_threshold:
                return SemanticDuplicateMatch(
                    is_duplicate=True,
                    similarity=similarity / 100.0,
                    reason=f"Fuzzy title match ({similarity}% >= {fuzzy_threshold}%)",
                    existing_ref=entry.ref,
                    existing_title=entry.title,
                    existing_source=entry.source,
                    match_type="fuzzy",
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
    Find all duplicate pairs in a list of tenders.
    """
    duplicates = []
    index = build_semantic_index([])

    for tender in tenders:
        match = find_semantic_duplicate(
            tender,
            existing_index=index,
            semantic_threshold=semantic_threshold,
            fuzzy_threshold=fuzzy_threshold,
            date_window_days=date_window_days,
            require_same_source=require_same_source,
        )

        if match:
            existing_tender = None
            if match.existing_ref:
                existing_entry = index.ref_map.get(match.existing_ref)
                if existing_entry is not None:
                    existing_tender = existing_entry.tender
            duplicates.append((tender, existing_tender, match))

        index.add_tender(tender)

    return duplicates


def merge_duplicate_info(
    original: Dict, duplicate: Dict, match_info: SemanticDuplicateMatch
) -> Dict:
    """
    Merge information from duplicate tender into original.
    """
    if "duplicate_refs" not in original:
        original["duplicate_refs"] = []

    dup_ref = duplicate.get("ref", "Unknown")
    if dup_ref not in original["duplicate_refs"]:
        original["duplicate_refs"].append(dup_ref)

    orig_desc = original.get("description", "")
    dup_desc = duplicate.get("description", "")
    if len(dup_desc) > len(orig_desc):
        original["description"] = dup_desc
        original["description_enhanced"] = True

    orig_url = original.get("url", "")
    dup_url = duplicate.get("url", "")
    if dup_url and dup_url != orig_url:
        if "additional_urls" not in original:
            original["additional_urls"] = []
        if dup_url not in original["additional_urls"]:
            original["additional_urls"].append(dup_url)

    original["duplicate_match_info"] = {
        "similarity": match_info.similarity,
        "match_type": match_info.match_type,
        "reason": match_info.reason,
        "duplicate_source": match_info.existing_source,
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
    Filter out duplicate tenders from a list.
    """
    started = perf_counter()

    if keep_first:
        filtered = []
        duplicates = []
        index = build_semantic_index([])

        for tender in tenders:
            match = find_semantic_duplicate(
                tender,
                existing_index=index,
                semantic_threshold=semantic_threshold,
                fuzzy_threshold=fuzzy_threshold,
                date_window_days=date_window_days,
                require_same_source=require_same_source,
            )

            if match:
                original = None
                if match.existing_ref:
                    existing_entry = index.ref_map.get(match.existing_ref)
                    if existing_entry is not None:
                        original = existing_entry.tender
                if original is not None:
                    merge_duplicate_info(original, tender, match)
                    duplicates.append((tender, original, match))
                else:
                    filtered.append(tender)
                    index.add_tender(tender)
            else:
                filtered.append(tender)
                index.add_tender(tender)

        logger.info(
            "Semantic duplicate filter checked %s tenders in %.2fs; kept=%s removed=%s",
            len(tenders),
            perf_counter() - started,
            len(filtered),
            len(duplicates),
        )
        return filtered, duplicates

    all_duplicates = find_all_semantic_duplicates(
        tenders,
        semantic_threshold=semantic_threshold,
        fuzzy_threshold=fuzzy_threshold,
        date_window_days=date_window_days,
        require_same_source=require_same_source,
    )

    refs_to_remove = {match_info.existing_ref for _, _, match_info in all_duplicates}
    filtered = [tender for tender in tenders if tender.get("ref", "") not in refs_to_remove]

    logger.info(
        "Semantic duplicate scan found %s duplicate pairs in %.2fs",
        len(all_duplicates),
        perf_counter() - started,
    )
    return filtered, all_duplicates


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    test_tenders = [
        {
            "ref": "NT-001",
            "title": "Supply of water treatment chemicals",
            "description": "Supply and delivery of cooling water treatment chemicals",
            "source": "National Treasury",
            "closing_date": "2025-01-15",
        },
        {
            "ref": "NT-002",
            "title": "Provision of water treatment chemicals",
            "description": "Supply and delivery of cooling water treatment chemicals",
            "source": "National Treasury",
            "closing_date": "2025-01-15",
        },
        {
            "ref": "ESK-001",
            "title": "Pump supply for power station",
            "description": "Supply of centrifugal pumps",
            "source": "Eskom",
            "closing_date": "2025-01-20",
        },
    ]

    print("=" * 60)
    print("SEMANTIC DUPLICATE DETECTOR TEST")
    print("=" * 60)

    for i in range(1, len(test_tenders)):
        print(f"\nChecking tender {i}: {test_tenders[i]['title']}")

        match = find_semantic_duplicate(
            test_tenders[i],
            test_tenders[:i],
            semantic_threshold=0.85,
            fuzzy_threshold=80,
        )

        if match:
            print("  ✅ DUPLICATE FOUND:")
            print(f"     Type: {match.match_type}")
            print(f"     Similarity: {match.similarity:.2%}")
            print(f"     Reason: {match.reason}")
            print(f"     Existing: {match.existing_title} ({match.existing_ref})")
        else:
            print("  ❌ No duplicate found")

    print("\n" + "=" * 60)
    print("FILTERING TEST")
    print("=" * 60)

    filtered, duplicates = filter_duplicates(test_tenders, semantic_threshold=0.85)

    print(f"\nOriginal: {len(test_tenders)} tenders")
    print(f"Filtered: {len(filtered)} tenders")
    print(f"Duplicates found: {len(duplicates)}")

    print("\nFiltered tenders:")
    for tender in filtered:
        print(f"  - {tender['ref']}: {tender['title']}")
