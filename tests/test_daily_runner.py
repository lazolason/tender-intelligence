import json
import sys
from types import ModuleType

import daily_runner


def test_run_daily_writes_status_and_reports_step_results(tmp_path, monkeypatch):
    status_path = tmp_path / "output" / "last_daily_run.json"
    calls = []

    tenderscan_module = ModuleType("tenderscan")

    def fake_run_all_scrapers(monitor=None):
        calls.append("run_all_scrapers")
        return [
            {
                "ref": "DAILY-001",
                "title": "Cooling water treatment chemicals",
                "description": "Condenser treatment chemicals",
                "client": "Eskom",
                "source": "Eskom",
                "url": "https://example.com/tender",
                "closing_date": "2099-04-30",
                "category": "MEXEL",
            },
            {
                "ref": "DAILY-BAD",
                "title": "",
                "description": "Missing title must not reach persistence",
                "client": "Eskom",
                "source": "Eskom",
                "closing_date": "2099-04-30",
                "category": "MEXEL",
            },
        ]

    def fake_process_tenders(tenders, *, return_stats=False):
        calls.append(("process_tenders", len(tenders)))
        result = (1, [{"ref": "DAILY-001", "scores": {"priority": "HIGH"}}])
        if return_stats:
            return (*result, {
                "inserted": 1,
                "updated": 0,
                "unchanged": 0,
                "semantic_skipped": 0,
                "excluded": 0,
            })
        return result

    def fake_save_outputs(new_items, *, validation_report_text=""):
        calls.append(("save_outputs", len(new_items), "Invalid: 1" in validation_report_text))

    tenderscan_module.run_all_scrapers = fake_run_all_scrapers
    tenderscan_module.process_tenders = fake_process_tenders
    tenderscan_module.save_outputs = fake_save_outputs

    logging_module = ModuleType("utils.logging_tools")
    logging_module.write_log = lambda *args, **kwargs: None
    logging_module.rotate_log_if_needed = lambda *args, **kwargs: None

    scraper_monitor_module = ModuleType("utils.scraper_monitor")

    class FakeMonitor:
        def __init__(self, output_dir=None, db_path=None):
            self.output_dir = output_dir
            self.db_path = db_path

        def generate_report(self):
            calls.append("generate_report")

        def should_alert_on_failures(self, threshold=3):
            calls.append(("should_alert_on_failures", threshold))
            return False, {}

        def get_metrics(self):
            return {}

    scraper_monitor_module.ScraperMonitor = FakeMonitor

    procurement_plans_module = ModuleType("sync_procurement_plans")
    procurement_plans_module.sync_procurement_plans = lambda: {
        "status": "success",
        "fetched": 2,
        "persisted": 2,
    }

    sync_dashboard_module = ModuleType("sync_dashboard")
    sync_dashboard_module.sync = lambda: True

    email_alerts_module = ModuleType("utils.email_alerts")
    email_alerts_module.EMAIL_CONFIG = {"sender_email": "ops@example.com"}
    email_alerts_module.send_daily_digest = lambda: True

    backup_module = ModuleType("utils.backup_database")
    backup_module.backup_database = lambda: True

    monkeypatch.setitem(sys.modules, "tenderscan", tenderscan_module)
    monkeypatch.setitem(sys.modules, "utils.logging_tools", logging_module)
    monkeypatch.setitem(sys.modules, "utils.scraper_monitor", scraper_monitor_module)
    monkeypatch.setitem(sys.modules, "sync_procurement_plans", procurement_plans_module)
    monkeypatch.setitem(sys.modules, "sync_dashboard", sync_dashboard_module)
    monkeypatch.setitem(sys.modules, "utils.email_alerts", email_alerts_module)
    monkeypatch.setitem(sys.modules, "utils.backup_database", backup_module)
    monkeypatch.setattr(daily_runner, "DAILY_RUN_STATUS_PATH", str(status_path))

    results = daily_runner.run_daily()

    assert results["scan"]["status"] == "success"
    assert results["scan"]["total_scraped"] == 2
    assert results["scan"]["new_added"] == 1
    assert results["scan"]["validation"]["valid"] == 1
    assert results["scan"]["validation"]["invalid"] == 1
    assert results["scan"]["validation"]["error_counts"] == {"Missing title": 1}
    assert results["scan"]["persistence"]["inserted"] == 1
    assert results["scan"]["persistence"]["updated"] == 0
    assert results["scan"]["failed_sources_count"] == 0
    assert results["scan"]["failed_sources"] == []
    assert results["procurement_plans"]["status"] == "success"
    assert results["procurement_plans"]["persisted"] == 2
    assert results["sync"]["status"] == "success"
    assert results["email"]["status"] == "sent"
    assert calls[:4] == [
        "run_all_scrapers",
        "generate_report",
        ("should_alert_on_failures", 3),
        ("process_tenders", 1),
    ]
    assert ("save_outputs", 1, True) in calls

    persisted = json.loads(status_path.read_text(encoding="utf-8"))
    assert persisted["scan"]["status"] == "success"
    assert persisted["sync"]["status"] == "success"
    assert persisted["email"]["status"] == "sent"
