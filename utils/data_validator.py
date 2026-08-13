import logging
import re
from dataclasses import dataclass
from datetime import datetime, timedelta, date
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse

import requests
from utils.retry_tools import secure_request_kwargs, validate_outbound_url
from utils.text_utils import parse_date


logger = logging.getLogger(__name__)


DEFAULT_ALLOWED_SOURCES = [
    "National Treasury",
    "City of Cape Town",
    "Rand Water",
    "Johannesburg Water",
    "Transnet",
    "Eskom",
    "SANRAL",
    "Anglo American",
    "Harmony Gold",
    "Seriti Resources",
    "Umgeni Water",
    "Magalies Water",
    "Lepelle Northern Water",
    "Unknown",
]

DEFAULT_ALLOWED_CATEGORIES = [
    "MEXEL",
    "PHAKATHI",
    "Exclude",
    "EXCLUDED",
    "Unknown",
]


@dataclass(frozen=True)
class ValidationResult:
    valid: bool
    errors: List[str]
    warnings: List[str]


class TenderValidator:
    def __init__(
        self,
        *,
        allowed_sources: Optional[List[str]] = None,
        allowed_categories: Optional[List[str]] = None,
        closing_date_grace_days: int = 1,
        check_url_reachable: bool = True,
        url_timeout_seconds: int = 8,
        require_url: bool = False,
    ):
        self.allowed_sources = set(
            DEFAULT_ALLOWED_SOURCES if allowed_sources is None else allowed_sources
        )
        self.allowed_categories = set(
            DEFAULT_ALLOWED_CATEGORIES if allowed_categories is None else allowed_categories
        )
        self.closing_date_grace_days = int(closing_date_grace_days)
        self.check_url_reachable = bool(check_url_reachable)
        self.url_timeout_seconds = int(url_timeout_seconds)
        self.require_url = bool(require_url)

        self._url_reachability_cache: Dict[str, bool] = {}

    def validate(self, tender: dict) -> Tuple[bool, List[str]]:
        result = self.validate_with_warnings(tender)
        return result.valid, result.errors

    def validate_with_warnings(self, tender: dict) -> ValidationResult:
        errors: List[str] = []
        warnings: List[str] = []

        ref = (tender.get("ref") or "").strip()
        if not ref:
            errors.append("Missing ref")
        elif len(ref) > 50:
            errors.append("ref exceeds 50 chars")

        title = (tender.get("title") or "").strip()
        if not title:
            errors.append("Missing title")
        elif len(title) > 500:
            errors.append("title exceeds 500 chars")

        source = (tender.get("source") or "").strip()
        if not source:
            errors.append("Missing source")
        elif self.allowed_sources and source not in self.allowed_sources:
            errors.append(f"Invalid source: {source}")

        category = (tender.get("category") or "Unknown").strip()
        if not category:
            errors.append("Missing category")
        elif self.allowed_categories and category not in self.allowed_categories:
            errors.append(f"Invalid category: {category}")

        closing_raw = (tender.get("closing_date") or "").strip()
        if closing_raw:
            closing_date = self._parse_date_to_date(closing_raw)
            if closing_date is None:
                errors.append("Invalid closing_date format")
            else:
                grace = timedelta(days=self.closing_date_grace_days)
                today = datetime.now().date()
                if closing_date < (today - grace):
                    errors.append("closing_date is in the past")

        url = (tender.get("url") or "").strip()
        if url:
            if not self._is_valid_url(url):
                errors.append("Invalid url format")
            elif self.check_url_reachable:
                ok = self._is_url_reachable(url)
                if not ok:
                    errors.append("url not reachable")
        else:
            if self.require_url:
                errors.append("Missing url")
            else:
                warnings.append("Missing url")

        return ValidationResult(valid=(len(errors) == 0), errors=errors, warnings=warnings)

    def _parse_date_to_date(self, value: str) -> Optional[date]:
        # Use shared parse_date function
        return parse_date(value)

    def _is_valid_url(self, url: str) -> bool:
        try:
            parsed = urlparse(url)
            if parsed.scheme not in ("http", "https"):
                return False
            if not parsed.netloc:
                return False
            if len(url) > 2048:
                return False
            return True
        except Exception:
            return False

    def _is_url_reachable(self, url: str) -> bool:
        if url in self._url_reachability_cache:
            return self._url_reachability_cache[url]

        headers = {"User-Agent": "TenderIntelligence/1.0"}

        try:
            validate_outbound_url(url)
            resp = requests.head(
                url,
                **secure_request_kwargs({
                    "headers": headers,
                    "timeout": self.url_timeout_seconds,
                    "allow_redirects": True,
                }),
            )
            validate_outbound_url(resp.url)
            ok = 200 <= resp.status_code < 400
            self._url_reachability_cache[url] = ok
            return ok
        except Exception:
            pass

        # Some sites block HEAD; fall back to a light GET.
        try:
            resp = requests.get(
                url,
                **secure_request_kwargs({
                    "headers": headers,
                    "timeout": self.url_timeout_seconds,
                    "allow_redirects": True,
                    "stream": True,
                }),
            )
            validate_outbound_url(resp.url)
            ok = 200 <= resp.status_code < 400
            self._url_reachability_cache[url] = ok
            return ok
        except Exception as exc:
            logger.warning("URL reachability check failed: %s (%s)", url, exc)
            self._url_reachability_cache[url] = False
            return False


def format_validation_report(
    *,
    total: int,
    valid_count: int,
    invalid_count: int,
    error_counts: Dict[str, int],
    invalid_examples: List[str],
    warning_counts: Optional[Dict[str, int]] = None,
) -> str:
    lines: List[str] = []
    lines.append("\n\nVALIDATION REPORT:")
    lines.append("=" * 40)
    lines.append(f"Total scraped: {total}")
    lines.append(f"Valid: {valid_count}")
    lines.append(f"Invalid: {invalid_count}")

    if error_counts:
        lines.append("\nTop validation errors:")
        for msg, count in sorted(error_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
            lines.append(f"  - {msg}: {count}")

    if warning_counts:
        lines.append("\nTop validation warnings:")
        for msg, count in sorted(warning_counts.items(), key=lambda kv: (-kv[1], kv[0]))[:20]:
            lines.append(f"  - {msg}: {count}")

    if invalid_examples:
        lines.append("\nInvalid tender samples:")
        for ex in invalid_examples[:20]:
            lines.append(f"  - {ex}")

    return "\n".join(lines) + "\n"
