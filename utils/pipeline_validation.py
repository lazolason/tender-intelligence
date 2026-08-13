"""Canonical batch validation used by every tender-processing entrypoint."""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from typing import Callable, Dict, Iterable, List, Optional

from utils.data_validator import TenderValidator, format_validation_report


@dataclass(frozen=True)
class BatchValidationResult:
    valid_tenders: List[dict]
    total: int
    valid_count: int
    invalid_count: int
    warning_count: int
    error_counts: Dict[str, int]
    warning_counts: Dict[str, int]
    invalid_examples: List[str]
    report_text: str

    def metrics(self) -> Dict[str, object]:
        """Return JSON-safe metrics for run status and monitoring."""
        return {
            "total": self.total,
            "valid": self.valid_count,
            "invalid": self.invalid_count,
            "warnings": self.warning_count,
            "error_counts": dict(self.error_counts),
            "warning_counts": dict(self.warning_counts),
        }


def build_pipeline_validator() -> TenderValidator:
    """Build the validator policy shared by CLI, scheduler, and rescue runs."""
    return TenderValidator(
        allowed_sources=[],
        check_url_reachable=False,
        require_url=False,
    )


def validate_tender_batch(
    tenders: Iterable[dict],
    *,
    validator: Optional[TenderValidator] = None,
    on_invalid: Optional[Callable[[str], None]] = None,
    max_examples: int = 20,
) -> BatchValidationResult:
    """Validate a batch once and return accepted records plus audit metrics."""
    tender_list = list(tenders or [])
    active_validator = validator or build_pipeline_validator()
    valid_tenders: List[dict] = []
    error_counts: Counter[str] = Counter()
    warning_counts: Counter[str] = Counter()
    invalid_examples: List[str] = []

    for item in tender_list:
        if not isinstance(item, dict):
            errors = ["Tender record must be an object"]
            source = "Unknown"
            ref = "NA"
            warnings: List[str] = []
            is_valid = False
        else:
            result = active_validator.validate_with_warnings(item)
            errors = result.errors
            warnings = result.warnings
            is_valid = result.valid
            source = item.get("source") or "Unknown"
            ref = item.get("ref") or "NA"

        warning_counts.update(warnings)
        if is_valid:
            valid_tenders.append(item)
            continue

        error_counts.update(errors)
        message = f"Invalid tender {ref} ({source}): {', '.join(errors)}"
        if on_invalid:
            on_invalid(message)
        if len(invalid_examples) < max_examples:
            invalid_examples.append(f"{ref} ({source}): {', '.join(errors)}")

    invalid_count = len(tender_list) - len(valid_tenders)
    report_text = format_validation_report(
        total=len(tender_list),
        valid_count=len(valid_tenders),
        invalid_count=invalid_count,
        error_counts=dict(error_counts),
        warning_counts=dict(warning_counts),
        invalid_examples=invalid_examples,
    )
    return BatchValidationResult(
        valid_tenders=valid_tenders,
        total=len(tender_list),
        valid_count=len(valid_tenders),
        invalid_count=invalid_count,
        warning_count=sum(warning_counts.values()),
        error_counts=dict(error_counts),
        warning_counts=dict(warning_counts),
        invalid_examples=invalid_examples,
        report_text=report_text,
    )
