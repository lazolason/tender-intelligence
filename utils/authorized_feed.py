"""Secure ingestion boundary for licensed or explicitly authorized local exports."""

from __future__ import annotations

import csv
import hashlib
import io
import json
import re
import sqlite3
from pathlib import Path
from typing import Any, Dict, List, Tuple

from classify_engine import classify_tender
from utils.db_writer import DatabaseWriter
from utils.pipeline_validation import validate_tender_batch
from utils.procurement_plan_linker import link_planned_opportunities


_CANONICAL_FIELDS = {
    "ref", "title", "description", "client", "closing_date", "url",
}
_SOURCE_ID_RE = re.compile(r"^[a-z0-9][a-z0-9_-]{1,63}$")


class AuthorizedFeedError(ValueError):
    """Raised when a feed violates the configured authorization boundary."""


def _source_config(config: Dict[str, Any], source_id: str) -> Tuple[Dict, Dict]:
    feed_config = config.get("authorized_feeds") or {}
    if not feed_config.get("enabled", False):
        raise AuthorizedFeedError("Authorized feed ingestion is disabled")
    matches = [
        source for source in feed_config.get("sources", [])
        if source.get("id") == source_id
    ]
    if len(matches) != 1 or not matches[0].get("enabled", False):
        raise AuthorizedFeedError("Feed source is not explicitly enabled")
    source = matches[0]
    if not _SOURCE_ID_RE.fullmatch(source_id):
        raise AuthorizedFeedError("Feed source id is invalid")
    if source.get("format") not in {"json", "csv"}:
        raise AuthorizedFeedError("Feed format is not supported")
    if source.get("kind", "live_tenders") != "live_tenders":
        raise AuthorizedFeedError("Feed kind is not supported")
    return feed_config, source


def _confined_file(inbox_dir: str, supplied_path: str, expected_format: str) -> Path:
    root = Path(inbox_dir).expanduser().resolve()
    candidate_input = Path(supplied_path).expanduser()
    candidate = (candidate_input if candidate_input.is_absolute() else root / candidate_input)
    if candidate.is_symlink():
        raise AuthorizedFeedError("Symbolic-link feed files are not allowed")
    resolved = candidate.resolve(strict=True)
    try:
        resolved.relative_to(root)
    except ValueError as exc:
        raise AuthorizedFeedError("Feed file must remain inside the configured inbox") from exc
    if not resolved.is_file():
        raise AuthorizedFeedError("Feed path must be a regular file")
    if resolved.suffix.casefold() != f".{expected_format}":
        raise AuthorizedFeedError("Feed file extension does not match its configured format")
    return resolved


def _read_bounded(path: Path, max_bytes: int) -> bytes:
    size = path.stat().st_size
    if size > max_bytes:
        raise AuthorizedFeedError(f"Feed file exceeds the {max_bytes}-byte limit")
    content = path.read_bytes()
    if len(content) > max_bytes:
        raise AuthorizedFeedError(f"Feed file exceeds the {max_bytes}-byte limit")
    return content


def _parse_records(content: bytes, file_format: str, max_records: int) -> List[Dict]:
    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise AuthorizedFeedError("Feed file must be UTF-8 encoded") from exc

    if file_format == "json":
        try:
            payload = json.loads(text)
        except json.JSONDecodeError as exc:
            raise AuthorizedFeedError("Feed JSON is malformed") from exc
        records = payload.get("records") if isinstance(payload, dict) else payload
    else:
        records = list(csv.DictReader(io.StringIO(text)))

    if not isinstance(records, list):
        raise AuthorizedFeedError("Feed must contain an array of records")
    if len(records) > max_records:
        raise AuthorizedFeedError(f"Feed exceeds the {max_records}-record limit")
    if any(not isinstance(record, dict) for record in records):
        raise AuthorizedFeedError("Every feed record must be an object")
    return records


def _namespaced_ref(source_id: str, raw_ref: str) -> str:
    raw = re.sub(r"[^A-Za-z0-9._/-]+", "-", (raw_ref or "").strip()).strip("-")
    if not raw:
        return ""
    prefix = "AF-" + re.sub(r"[^A-Z0-9]+", "-", source_id.upper()).strip("-")
    candidate = f"{prefix}-{raw}"
    if len(candidate) <= 50:
        return candidate
    digest = hashlib.sha256(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"{prefix[:35]}-{digest}"[:50]


def _normalize_records(records: List[Dict], source: Dict) -> List[Dict]:
    field_map = source.get("field_map") or {}
    unknown_fields = set(field_map) - _CANONICAL_FIELDS
    if unknown_fields or any(not isinstance(value, str) for value in field_map.values()):
        raise AuthorizedFeedError("Feed field_map contains unsupported mappings")

    def value(record: Dict, field: str):
        return record.get(field_map.get(field, field))

    normalized = []
    source_label = f"Authorized Feed: {source['label']}"
    for record in records:
        title = str(value(record, "title") or "").strip()
        normalized.append({
            "ref": _namespaced_ref(source["id"], str(value(record, "ref") or "")),
            "title": title,
            "description": str(value(record, "description") or title).strip(),
            "client": str(
                value(record, "client") or source.get("default_client") or ""
            ).strip(),
            "closing_date": str(value(record, "closing_date") or "").strip(),
            "url": str(value(record, "url") or "").strip(),
            # Never trust a record to choose its own provenance.
            "source": source_label,
        })
    return normalized


def _reserve_audit_run(
    db_path: str,
    *,
    source_id: str,
    file_name: str,
    digest: str,
    dry_run: bool,
) -> Tuple[int, bool]:
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute("BEGIN IMMEDIATE")
        row = conn.execute(
            "SELECT id, status FROM authorized_feed_runs "
            "WHERE source_id = ? AND file_sha256 = ? AND dry_run = ?",
            (source_id, digest, int(dry_run)),
        ).fetchone()
        if row and row[1] in {"RUNNING", "SUCCESS"}:
            return int(row[0]), True
        if row:
            conn.execute(
                "UPDATE authorized_feed_runs SET status = 'RUNNING', error_type = NULL, "
                "started_at = CURRENT_TIMESTAMP, finished_at = NULL WHERE id = ?",
                (row[0],),
            )
            return int(row[0]), False
        cursor = conn.execute(
            "INSERT INTO authorized_feed_runs "
            "(source_id, file_name, file_sha256, dry_run, status) "
            "VALUES (?, ?, ?, ?, 'RUNNING')",
            (source_id, file_name, digest, int(dry_run)),
        )
        return int(cursor.lastrowid), False


def _finish_audit(db_path: str, run_id: int, result: Dict[str, Any]) -> None:
    with sqlite3.connect(db_path, timeout=10.0) as conn:
        conn.execute(
            "UPDATE authorized_feed_runs SET status = ?, records_total = ?, "
            "records_valid = ?, records_invalid = ?, records_excluded = ?, "
            "records_inserted = ?, records_updated = ?, records_unchanged = ?, "
            "error_type = ?, finished_at = CURRENT_TIMESTAMP WHERE id = ?",
            (
                result["status"], result.get("total", 0), result.get("valid", 0),
                result.get("invalid", 0), result.get("excluded", 0),
                result.get("inserted", 0), result.get("updated", 0),
                result.get("unchanged", 0), result.get("error_type"), run_id,
            ),
        )


def ingest_authorized_feed(
    *,
    config: Dict[str, Any],
    source_id: str,
    file_path: str,
    db_path: str,
    dry_run: bool = False,
) -> Dict[str, Any]:
    """Validate and ingest one explicitly allowlisted local export."""
    feed_config, source = _source_config(config, source_id)
    path = _confined_file(
        feed_config.get("inbox_dir", "data/authorized_feeds/inbox"),
        file_path,
        source["format"],
    )
    content = _read_bounded(path, int(feed_config.get("max_file_bytes", 10 * 1024 * 1024)))
    digest = hashlib.sha256(content).hexdigest()

    writer = DatabaseWriter(db_path)
    run_id, duplicate = _reserve_audit_run(
        db_path,
        source_id=source_id,
        file_name=path.name,
        digest=digest,
        dry_run=dry_run,
    )
    if duplicate:
        return {
            "status": "duplicate",
            "source_id": source_id,
            "file_sha256": digest,
            "dry_run": dry_run,
            "run_id": run_id,
        }

    result: Dict[str, Any] = {
        "status": "FAILED",
        "source_id": source_id,
        "file_sha256": digest,
        "dry_run": dry_run,
        "run_id": run_id,
        "total": 0,
        "valid": 0,
        "invalid": 0,
        "excluded": 0,
        "inserted": 0,
        "updated": 0,
        "unchanged": 0,
    }
    try:
        records = _parse_records(
            content,
            source["format"],
            int(feed_config.get("max_records", 10000)),
        )
        normalized = _normalize_records(records, source)
        validation = validate_tender_batch(normalized)
        result.update({
            "total": validation.total,
            "valid": validation.valid_count,
            "invalid": validation.invalid_count,
            "validation": validation.metrics(),
        })

        relevant = []
        for tender in validation.valid_tenders:
            classification = classify_tender(tender["title"], tender["description"])
            if classification.get("category") == "EXCLUDED":
                result["excluded"] += 1
            else:
                relevant.append(tender)

        result["ready"] = len(relevant)
        if not dry_run:
            for tender in relevant:
                action, _scores, _classification = writer.upsert_tender_with_scoring(tender)
                result[action] += 1
            if result["inserted"] or result["updated"]:
                result["plan_linkage"] = link_planned_opportunities(db_path)
        result["status"] = "SUCCESS"
        _finish_audit(db_path, run_id, result)
        return result
    except Exception as exc:
        result["error_type"] = type(exc).__name__
        _finish_audit(db_path, run_id, result)
        raise
