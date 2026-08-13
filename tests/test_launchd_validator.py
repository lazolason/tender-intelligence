import sys

import pytest

from utils.launchd_validator import inspect_default_launchd_jobs


@pytest.mark.skipif(sys.platform != "darwin", reason="launchd configuration is macOS-specific")
def test_launchd_jobs_point_to_current_repo():
    jobs = inspect_default_launchd_jobs()

    assert jobs["app"]["valid"] is True, jobs["app"]["issues"]
    assert jobs["daily"]["valid"] is True, jobs["daily"]["issues"]
    assert jobs["weekly"]["valid"] is True, jobs["weekly"]["issues"]

    assert jobs["app"]["target_path"].endswith("/serve_app.sh")
    assert jobs["app"]["run_at_load"] is True
    assert jobs["app"]["keep_alive"] is True
    assert jobs["daily"]["target_path"].endswith("/daily_runner.py")
    assert jobs["weekly"]["target_path"].endswith("/weekly_report.py")
    assert jobs["app"]["working_directory"] == jobs["daily"]["working_directory"] == jobs["weekly"]["working_directory"]
