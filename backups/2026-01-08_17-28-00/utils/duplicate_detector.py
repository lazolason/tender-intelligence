import logging
import re
from dataclasses import dataclass
from datetime import date
from typing import Dict, Iterable, Optional, Tuple

from dateutil import parser as date_parser

logger = logging.getLogger(__name__)


try:
    from fuzzywuzzy import fuzz as _fuzz  # type: ignore
except Exception:  # pragma: no cover
    _fuzz = None


@dataclass(frozen=True)
class DuplicateMatch:
    is_duplicate: bool
    similarity: int
    reason: str
    existing_ref: str
    existing_title: str
    existing_source: str


def _normalize_text(value: str) -> str:
    value = (value or "").strip().lower()
    value = re.sub(r"\s+", " ", value)
    value = re.sub(r"[^\w\s/.-]", " ", value)
    value = re.sub(r"\s+", " ", value).strip()
    return value


def _title_similarity(a: str, b: str) -> int:
    a = _normalize_text(a)
    b = _normalize_text(b)
    if not a or not b:
        return 0

    if _fuzz is not None:
        # token_set_ratio helps with reordered tokens / minor variations
        return int(max(_fuzz.ratio(a, b), _fuzz.token_set_ratio(a, b)))

    # Fallback if fuzzywuzzy isn't installed
    from difflib import SequenceMatcher

    return int(round(SequenceMatcher(a=a, b=b).ratio() * 100))


def _parse_date(value: str) -> Optional[date]:
    value = (value or "").strip()
    if not value:
        return None
    try:
        return date_parser.parse(value, dayfirst=True, fuzzy=True).date()
    except Exception:
        return None


def _within_days(a: Optional[date], b: Optional[date], *, days: int) -> bool:
    if a is None or b is None:
        return False
    return abs((a - b).days) <= int(days)


def find_duplicate(
    new_tender: Dict,
    existing_tenders: Iterable[Dict],
    *,
    threshold: int = 85,
    date_window_days: int = 7,
    require_same_source: bool = True,
) -> Optional[DuplicateMatch]:
    new_ref = (new_tender.get("ref") or "").strip().upper()
    new_title = (new_tender.get("title") or "").strip()
    new_source = (new_tender.get("source") or "Unknown").strip()
    new_closing = _parse_date(new_tender.get("closing_date") or "")

    if not new_title:
        return None

    for existing in existing_tenders:
        ex_ref = (existing.get("ref") or "").strip().upper()
        ex_title = (existing.get("title") or "").strip()
        ex_source = (existing.get("source") or "Unknown").strip()
        ex_closing = _parse_date(existing.get("closing_date") or "")

        if new_ref and ex_ref and new_ref != "NA" and new_ref == ex_ref:
            return DuplicateMatch(
                is_duplicate=True,
                similarity=100,
                reason="Exact ref match",
                existing_ref=ex_ref,
                existing_title=ex_title,
                existing_source=ex_source,
            )

        similarity = _title_similarity(new_title, ex_title)
        if similarity < int(threshold):
            continue

        same_source = _normalize_text(new_source) == _normalize_text(ex_source)
        close_date = _within_days(new_closing, ex_closing, days=date_window_days)

        if require_same_source and not same_source:
            continue

        if same_source and (close_date or date_window_days <= 0 or (new_closing is None or ex_closing is None)):
            return DuplicateMatch(
                is_duplicate=True,
                similarity=similarity,
                reason=f"Fuzzy title match (>= {threshold}%)",
                existing_ref=ex_ref,
                existing_title=ex_title,
                existing_source=ex_source,
            )

    return None


def find_best_title_match(
    new_tender: Dict,
    existing_tenders: Iterable[Dict],
) -> Optional[Tuple[int, Dict]]:
    new_title = (new_tender.get("title") or "").strip()
    if not new_title:
        return None

    best_similarity = -1
    best_existing = None

    for existing in existing_tenders:
        ex_title = (existing.get("title") or "").strip()
        similarity = _title_similarity(new_title, ex_title)
        if similarity > best_similarity:
            best_similarity = similarity
            best_existing = existing

    if best_existing is None:
        return None

    return int(best_similarity), best_existing
