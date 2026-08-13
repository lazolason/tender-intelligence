"""Conservative, auditable linkage of procurement plans to live tenders."""

from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from difflib import SequenceMatcher
from typing import Dict, Iterable, List, Optional, Set, Tuple

from utils.text_utils import parse_date


_WORD_RE = re.compile(r"[a-z0-9]+")
_SCOPE_STOPWORDS = {
    "a", "an", "and", "as", "at", "be", "by", "for", "from", "in", "of",
    "on", "or", "the", "to", "with", "appointment", "bid", "contract",
    "delivery", "goods", "period", "procurement", "project", "provider",
    "provision", "services", "service", "supply", "tender", "works", "year",
    "years", "month", "months", "required", "basis",
}
_ORG_STOPWORDS = {
    "limited", "ltd", "pty", "holdings", "company", "soc", "incorporated",
    "the", "of", "south", "africa", "african",
}
_ORG_ALIASES = {
    "state information technology agency": "sita",
    "sita": "sita",
    "south african revenue service": "sars",
    "sars": "sars",
    "passenger rail agency of south africa": "prasa",
    "prasa": "prasa",
    "council for scientific and industrial research": "csir",
    "csir": "csir",
}


@dataclass(frozen=True)
class LinkCandidate:
    external_id: str
    tender_ref: str
    score: float
    institution_score: float
    scope_score: float
    overlap_tokens: Tuple[str, ...]

    def evidence(self) -> Dict[str, object]:
        return {
            "institution_score": round(self.institution_score, 4),
            "scope_score": round(self.scope_score, 4),
            "overlap_tokens": list(self.overlap_tokens),
        }


def _normalized_words(value: str) -> List[str]:
    return _WORD_RE.findall((value or "").casefold())


def _scope_tokens(value: str) -> Set[str]:
    return {
        word for word in _normalized_words(value)
        if len(word) >= 3 and word not in _SCOPE_STOPWORDS
    }


def _organization_key(value: str) -> Tuple[str, Set[str]]:
    normalized = " ".join(_normalized_words(value))
    if normalized in _ORG_ALIASES:
        alias = _ORG_ALIASES[normalized]
        return alias, {alias}
    tokens = {word for word in normalized.split() if word not in _ORG_STOPWORDS}
    return " ".join(sorted(tokens)), tokens


def _institution_similarity(institution: str, client: str) -> float:
    left_key, left = _organization_key(institution)
    right_key, right = _organization_key(client)
    if not left or not right:
        return 0.0
    if left_key == right_key:
        return 1.0
    overlap = left & right
    if len(overlap) < 2:
        return 0.0
    containment = len(overlap) / min(len(left), len(right))
    jaccard = len(overlap) / len(left | right)
    return 0.7 * containment + 0.3 * jaccard


def score_plan_tender(plan: Dict, tender: Dict) -> Optional[LinkCandidate]:
    """Score a candidate, returning None when a mandatory guard fails."""
    if plan.get("category") != tender.get("category"):
        return None

    institution_score = _institution_similarity(
        plan.get("institution", ""), tender.get("client", "")
    )
    if institution_score < 0.9:
        return None

    plan_text = plan.get("description", "")
    tender_title = tender.get("title", "")
    tender_text = f"{tender_title} {tender.get('description', '')}"
    plan_tokens = _scope_tokens(plan_text)
    tender_tokens = _scope_tokens(tender_text)
    overlap = plan_tokens & tender_tokens
    if len(plan_tokens) < 4 or len(tender_tokens) < 4 or len(overlap) < 4:
        return None

    containment = len(overlap) / min(len(plan_tokens), len(tender_tokens))
    jaccard = len(overlap) / len(plan_tokens | tender_tokens)
    phrase_ratio = max(
        SequenceMatcher(None, " ".join(_normalized_words(plan_text)), " ".join(_normalized_words(tender_title))).ratio(),
        SequenceMatcher(None, " ".join(sorted(plan_tokens)), " ".join(sorted(tender_tokens))).ratio(),
    )
    scope_score = 0.55 * containment + 0.30 * jaccard + 0.15 * phrase_ratio

    advert_date = parse_date(plan.get("planned_advert_date") or "")
    closing_date = parse_date(tender.get("closing_date") or "")
    if advert_date and closing_date and closing_date < advert_date:
        return None

    score = 0.25 * institution_score + 0.75 * scope_score
    return LinkCandidate(
        external_id=plan["external_id"],
        tender_ref=tender["ref"],
        score=score,
        institution_score=institution_score,
        scope_score=scope_score,
        overlap_tokens=tuple(sorted(overlap)),
    )


def _select_unambiguous(
    candidates: Iterable[LinkCandidate],
    *,
    minimum_score: float,
    ambiguity_margin: float,
) -> Tuple[List[LinkCandidate], Dict[str, int]]:
    by_plan: Dict[str, List[LinkCandidate]] = {}
    for candidate in candidates:
        by_plan.setdefault(candidate.external_id, []).append(candidate)

    stats = {"below_threshold": 0, "ambiguous": 0, "tender_conflicts": 0}
    proposals: List[LinkCandidate] = []
    for plan_candidates in by_plan.values():
        ranked = sorted(plan_candidates, key=lambda item: item.score, reverse=True)
        best = ranked[0]
        if best.score < minimum_score:
            stats["below_threshold"] += 1
            continue
        if len(ranked) > 1 and best.score - ranked[1].score < ambiguity_margin:
            stats["ambiguous"] += 1
            continue
        proposals.append(best)

    by_tender: Dict[str, List[LinkCandidate]] = {}
    for candidate in proposals:
        by_tender.setdefault(candidate.tender_ref, []).append(candidate)

    selected: List[LinkCandidate] = []
    for tender_candidates in by_tender.values():
        ranked = sorted(tender_candidates, key=lambda item: item.score, reverse=True)
        if len(ranked) > 1 and ranked[0].score - ranked[1].score < ambiguity_margin:
            stats["tender_conflicts"] += len(ranked)
            continue
        selected.append(ranked[0])
    return selected, stats


def link_planned_opportunities(
    db_path: str,
    *,
    minimum_score: float = 0.86,
    ambiguity_margin: float = 0.08,
) -> Dict[str, int]:
    """Link high-confidence plan/tender pairs and persist an evidence audit."""
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        plans = [
            dict(row) for row in conn.execute(
                "SELECT * FROM planned_opportunities "
                "WHERE is_active = 1 AND matched_tender_ref IS NULL "
                "AND category IN ('MEXEL', 'PHAKATHI')"
            )
        ]
        tenders = [
            dict(row) for row in conn.execute(
                "SELECT ref, title, description, client, category, closing_date "
                "FROM tenders WHERE category IN ('MEXEL', 'PHAKATHI')"
            )
        ]

        candidates = [
            candidate
            for plan in plans
            for tender in tenders
            if (candidate := score_plan_tender(plan, tender)) is not None
        ]
        selected, selection_stats = _select_unambiguous(
            candidates,
            minimum_score=minimum_score,
            ambiguity_margin=ambiguity_margin,
        )

        conn.execute("BEGIN IMMEDIATE")
        linked = 0
        for candidate in selected:
            cursor = conn.execute(
                "UPDATE planned_opportunities SET matched_tender_ref = ?, "
                "lifecycle_stage = 'MATCHED' "
                "WHERE external_id = ? AND is_active = 1 AND matched_tender_ref IS NULL",
                (candidate.tender_ref, candidate.external_id),
            )
            if cursor.rowcount != 1:
                continue
            conn.execute(
                "INSERT INTO planned_opportunity_matches "
                "(external_id, tender_ref, match_score, match_method, evidence) "
                "VALUES (?, ?, ?, 'conservative_lexical_v1', ?)",
                (
                    candidate.external_id,
                    candidate.tender_ref,
                    round(candidate.score, 6),
                    json.dumps(candidate.evidence(), sort_keys=True),
                ),
            )
            linked += 1

    plans_with_candidates = {candidate.external_id for candidate in candidates}
    return {
        "plans_evaluated": len(plans),
        "no_candidate": len(plans) - len(plans_with_candidates),
        "tenders_evaluated": len(tenders),
        "eligible_candidates": len(candidates),
        "linked": linked,
        **selection_stats,
    }
