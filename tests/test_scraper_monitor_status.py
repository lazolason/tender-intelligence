from utils.scraper_monitor import summarize_scraper_health_status


def test_summarize_scraper_health_status_surfaces_latest_and_repeated_failures():
    summary = summarize_scraper_health_status(
        {
            "National Treasury": {"status": "failure", "consecutive_failures": 1},
            "Johannesburg Water": {"status": "success", "consecutive_failures": 0},
            "SOEs": {"status": "error", "consecutive_failures": 3},
        },
        problem_threshold=3,
    )

    assert summary["sources_tracked"] == 3
    assert summary["latest_failed_sources"] == ["National Treasury", "SOEs"]
    assert summary["problem_sources"] == ["SOEs"]
