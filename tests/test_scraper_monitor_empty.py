"""A clean scrape that yields nothing must not be reported as healthy.

Municipalities ran 66 times returning zero tenders while showing
status=success and success_rate=1.0, so scraper drift was invisible.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from utils.scraper_monitor import ScraperMonitor, summarize_scraper_health_status


def _monitor(tmp_path):
    return ScraperMonitor(metrics_path=str(tmp_path / "metrics.json"))


def test_empty_run_is_not_healthy(tmp_path):
    monitor = _monitor(tmp_path)
    with monitor.track("Municipalities") as run:
        run.tenders_found = 0

    metrics = monitor.get_metrics()["Municipalities"]
    assert metrics["status"] == "empty"
    assert metrics["consecutive_empty"] == 1
    # No exception was raised, so the failure counters stay clean.
    assert metrics["failures"] == 0


def test_empty_counter_accumulates_then_resets(tmp_path):
    monitor = _monitor(tmp_path)
    for _ in range(3):
        with monitor.track("Transnet") as run:
            run.tenders_found = 0
    assert monitor.get_metrics()["Transnet"]["consecutive_empty"] == 3

    with monitor.track("Transnet") as run:
        run.tenders_found = 4

    metrics = monitor.get_metrics()["Transnet"]
    assert metrics["status"] == "success"
    assert metrics["consecutive_empty"] == 0


def test_failure_resets_empty_counter(tmp_path):
    monitor = _monitor(tmp_path)
    with monitor.track("Seriti") as run:
        run.tenders_found = 0

    try:
        with monitor.track("Seriti"):
            raise RuntimeError("boom")
    except RuntimeError:
        pass

    metrics = monitor.get_metrics()["Seriti"]
    assert metrics["status"] == "failure"
    assert metrics["consecutive_empty"] == 0


def test_health_summary_surfaces_empty_sources():
    summary = summarize_scraper_health_status(
        {
            "Municipalities": {"status": "empty", "consecutive_empty": 66},
            "Eskom": {"status": "success", "consecutive_empty": 0},
            "Rand Water": {"status": "failure", "consecutive_failures": 1},
        }
    )
    assert summary["empty_sources"] == ["Municipalities"]
    assert summary["latest_failed_sources"] == ["Rand Water"]
