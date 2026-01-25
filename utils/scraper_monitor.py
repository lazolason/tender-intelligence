import json
import logging
import os
import time
import threading
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterator, Optional, Tuple


logger = logging.getLogger(__name__)


class CircuitOpenError(Exception):
    """Raised when a scraper is skipped because its circuit is open."""
    pass



def _utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def _safe_read_json(path: str) -> Dict[str, Any]:
    if not path or not os.path.exists(path):
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return data if isinstance(data, dict) else {}
    except Exception as exc:
        logger.warning("Failed to read monitor JSON %s: %s", path, exc)
        return {}


def _safe_write_json(path: str, payload: Dict[str, Any]) -> bool:
    if not path:
        return False
    try:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        tmp_path = f"{path}.tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, indent=2, sort_keys=True)
        os.replace(tmp_path, path)
        return True
    except Exception as exc:
        logger.warning("Failed to write monitor JSON %s: %s", path, exc)
        return False


@dataclass
class ScrapeRunContext:
    source: str
    tenders_found: Optional[int] = None


class ScraperMonitor:
    """
    Tracks per-source scraper reliability over time.
    Stores metrics in a JSON file and can generate a health report.
    """

    def __init__(self, *, metrics_path: Optional[str] = None, output_dir: Optional[str] = None):
        if metrics_path:
            self.metrics_path = metrics_path
        elif output_dir:
            self.metrics_path = os.path.join(output_dir, "scraper_metrics.json")
        else:
            self.metrics_path = os.path.join(os.path.dirname(__file__), "..", "output", "scraper_metrics.json")

        self._metrics: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.Lock()  # Thread safety for concurrent scraper access
        self._load()

    def _load(self) -> None:
        data = _safe_read_json(self.metrics_path)
        # Stored as top-level mapping: { "Source": { ... } }
        self._metrics = {k: v for k, v in data.items() if isinstance(v, dict)}

    def _save(self) -> None:
        with self._lock:  # Protect concurrent file writes
            _safe_write_json(self.metrics_path, self._metrics)

    @contextmanager
    def track(self, source: str, skip_if_circuit_open: bool = True) -> Iterator[ScrapeRunContext]:
        if skip_if_circuit_open and self.is_circuit_open(source):
            logger.info("Circuit open for %s. Skipping run.", source)
            raise CircuitOpenError(f"Circuit open for {source}")

        ctx = ScrapeRunContext(source=source)
        start = time.perf_counter()
        error: Optional[str] = None
        success = False
        try:
            yield ctx
            success = True
        except Exception as exc:
            error = str(exc)
            raise
        finally:
            duration = time.perf_counter() - start
            tenders_found = int(ctx.tenders_found or 0) if success else int(ctx.tenders_found or 0)
            self.record_run(
                source=source,
                success=success,
                tenders_found=tenders_found,
                duration=duration,
                error_message=error,
            )
            self._save()

    def record_run(
        self,
        *,
        source: str,
        success: bool,
        tenders_found: int,
        duration: float,
        error_message: Optional[str] = None,
    ) -> None:
        with self._lock:  # Protect concurrent updates to metrics
            source = (source or "Unknown").strip() or "Unknown"
            entry = dict(self._metrics.get(source) or {})

            total_runs = int(entry.get("total_runs") or 0) + 1
            failures = int(entry.get("failures") or 0)
            consecutive_failures = int(entry.get("consecutive_failures") or 0)
            total_tenders = int(entry.get("total_tenders") or 0)
            total_duration = float(entry.get("total_duration") or 0.0)

            if success:
                status = "success"
                total_tenders += int(tenders_found or 0)
                total_duration += float(duration or 0.0)
                consecutive_failures = 0
            else:
                status = "failure"
                failures += 1
                consecutive_failures += 1

            successes = max(0, total_runs - failures)
            success_rate = (successes / total_runs) if total_runs else 0.0
            avg_tenders = (total_tenders / successes) if successes else 0.0
            avg_duration = (total_duration / successes) if successes else 0.0

            entry.update(
                {
                    "last_run": _utc_now_iso(),
                    "status": status,
                    "tenders_found": int(tenders_found or 0),
                    "duration": float(round(float(duration or 0.0), 3)),
                    "success_rate": float(round(success_rate, 4)),
                    "total_runs": total_runs,
                    "failures": failures,
                    "consecutive_failures": consecutive_failures,
                    "avg_tenders": float(round(avg_tenders, 2)),
                    "avg_duration": float(round(avg_duration, 2)),
                }
            )

            if not success and error_message:
                entry["error_message"] = error_message[:500]
            elif success:
                entry.pop("error_message", None)

            self._metrics[source] = entry

    def get_metrics(self) -> Dict[str, Dict[str, Any]]:
        return dict(self._metrics)

    def is_circuit_open(self, source: str, threshold: int = 3, cooldown_seconds: int = 3600) -> bool:
        """
        Returns True if the source has failed `threshold` consecutive times
        and hasn't passed the `cooldown_seconds` period.
        """
        with self._lock:
            entry = self._metrics.get(source)
            if not entry:
                return False

            consecutive_failures = int(entry.get("consecutive_failures") or 0)
            if consecutive_failures < threshold:
                return False

            last_run_str = entry.get("last_run")
            if not last_run_str:
                return True

            try:
                # Basic iso-to-datetime parsing
                # (format: 2024-01-24T18:00:00Z)
                from dateutil.parser import parse
                last_run_time = parse(last_run_str)
                now = datetime.utcnow()
                
                # Check if we are still within the cooldown period
                seconds_since_last_run = (now - last_run_time.replace(tzinfo=None)).total_seconds()
                return seconds_since_last_run < cooldown_seconds
            except Exception:
                # If timestamp parsing fails, assume circuit is open if failures met
                return True

    def get_problem_sources(self, *, consecutive_failures_threshold: int = 3) -> Dict[str, Dict[str, Any]]:
        problems: Dict[str, Dict[str, Any]] = {}
        for source, entry in self._metrics.items():
            if int(entry.get("consecutive_failures") or 0) >= int(consecutive_failures_threshold):
                problems[source] = entry
        return problems

    def should_alert_on_failures(self, *, threshold: int = 3) -> Tuple[bool, Dict[str, Dict[str, Any]]]:
        """
        Alert when a source hits `threshold` consecutive failures, once per threshold event.
        """
        to_alert: Dict[str, Dict[str, Any]] = {}
        for source, entry in self._metrics.items():
            consecutive = int(entry.get("consecutive_failures") or 0)
            if consecutive < int(threshold):
                continue
            last_alerted = int(entry.get("last_alerted_consecutive_failures") or 0)
            if consecutive == int(threshold) and last_alerted != int(threshold):
                to_alert[source] = entry
        return (len(to_alert) > 0), to_alert

    def mark_alerted(self, sources: Dict[str, Dict[str, Any]], *, threshold: int = 3) -> None:
        for source in sources.keys():
            entry = dict(self._metrics.get(source) or {})
            entry["last_alerted_consecutive_failures"] = int(threshold)
            self._metrics[source] = entry
        self._save()

    def generate_report(self, *, output_path: Optional[str] = None) -> Dict[str, Dict[str, Any]]:
        """
        Saves a health report (mapping source -> metrics) to output/scraper_health.json by default.
        """
        report = self.get_metrics()

        if not output_path:
            output_path = os.path.join(os.path.dirname(self.metrics_path), "scraper_health.json")

        _safe_write_json(output_path, report)
        return report

