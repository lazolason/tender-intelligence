"""
Helpers for validating local launchd plist configuration.
"""

from __future__ import annotations

import json
import os
import plistlib
import sys
import tempfile
from typing import Any, Dict

PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if PROJECT_DIR not in sys.path:
    sys.path.insert(0, PROJECT_DIR)

from utils.launchd_jobs import render_default_launchd_jobs


def inspect_launchd_job(
    plist_path: str,
    *,
    expected_label: str,
    expected_target_name: str,
    expected_schedule: Dict[str, int] | None = None,
    expected_run_at_load: bool | None = None,
    expected_keep_alive: bool | None = None,
    project_dir: str = PROJECT_DIR,
) -> Dict[str, Any]:
    """
    Inspect one launchd plist and return validation details.
    """
    info: Dict[str, Any] = {
        "path": plist_path,
        "exists": os.path.exists(plist_path),
        "expected_label": expected_label,
        "expected_target_name": expected_target_name,
        "valid": False,
        "issues": [],
    }

    if not info["exists"]:
        info["issues"].append("plist file missing")
        return info

    try:
        with open(plist_path, "rb") as file_obj:
            payload = plistlib.load(file_obj)
    except Exception as exc:
        info["issues"].append(f"failed to parse plist: {exc}")
        return info

    program_arguments = payload.get("ProgramArguments") or []
    working_directory = payload.get("WorkingDirectory")
    schedule = payload.get("StartCalendarInterval") or {}
    stdout_path = payload.get("StandardOutPath")
    stderr_path = payload.get("StandardErrorPath")
    run_at_load = payload.get("RunAtLoad")
    keep_alive = payload.get("KeepAlive")

    executable_path = program_arguments[0] if program_arguments else None
    target_path = program_arguments[1] if len(program_arguments) >= 2 else executable_path

    if payload.get("Label") != expected_label:
        info["issues"].append("label mismatch")
    if not executable_path or not os.path.exists(executable_path):
        info["issues"].append("executable missing")
    if not target_path or os.path.basename(target_path) != expected_target_name:
        info["issues"].append("entrypoint mismatch")
    if target_path and target_path != executable_path and not os.path.exists(target_path):
        info["issues"].append("entrypoint missing")
    if working_directory != project_dir:
        info["issues"].append("working directory mismatch")

    logs_dir = os.path.join(project_dir, "logs")
    for log_path, label in ((stdout_path, "stdout"), (stderr_path, "stderr")):
        if not log_path:
            info["issues"].append(f"{label} path missing")
        elif not os.path.dirname(log_path).startswith(logs_dir):
            info["issues"].append(f"{label} path outside repo logs directory")

    if expected_schedule:
        for key, expected_value in expected_schedule.items():
            if int(schedule.get(key, -1)) != int(expected_value):
                info["issues"].append(f"schedule mismatch for {key}")
    elif schedule:
        info["issues"].append("unexpected schedule")

    if expected_run_at_load is not None and bool(run_at_load) != expected_run_at_load:
        info["issues"].append("run-at-load mismatch")
    if expected_keep_alive is not None and bool(keep_alive) != expected_keep_alive:
        info["issues"].append("keep-alive mismatch")

    info.update(
        {
            "label": payload.get("Label"),
            "executable_path": executable_path,
            "target_path": target_path,
            "working_directory": working_directory,
            "schedule": schedule,
            "stdout_path": stdout_path,
            "stderr_path": stderr_path,
            "run_at_load": bool(run_at_load),
            "keep_alive": bool(keep_alive),
        }
    )
    info["valid"] = not info["issues"]
    return info


def inspect_default_launchd_jobs(
    project_dir: str = PROJECT_DIR,
    *,
    plist_dir: str | None = None,
    python_executable: str | None = None,
) -> Dict[str, Dict[str, Any]]:
    """
    Inspect checkout-specific launchd job definitions.

    Bundled plist files are templates so they never retain another user's
    checkout path.  Unless a rendered ``plist_dir`` is supplied, render those
    templates in a temporary directory before validating them.
    """
    if plist_dir is None:
        with tempfile.TemporaryDirectory(prefix="tenderscan-launchd-") as temp_dir:
            render_default_launchd_jobs(
                temp_dir,
                project_dir,
                python_executable=python_executable,
            )
            return _inspect_default_launchd_jobs(project_dir, temp_dir)
    return _inspect_default_launchd_jobs(project_dir, plist_dir)


def _inspect_default_launchd_jobs(
    project_dir: str, plist_dir: str
) -> Dict[str, Dict[str, Any]]:
    """Inspect previously rendered launchd jobs from ``plist_dir``."""
    return {
        "app": inspect_launchd_job(
            os.path.join(plist_dir, "com.tenderscan.app.plist"),
            expected_label="com.tenderscan.app",
            expected_target_name="serve_app.sh",
            expected_run_at_load=True,
            expected_keep_alive=True,
            project_dir=project_dir,
        ),
        "daily": inspect_launchd_job(
            os.path.join(plist_dir, "com.tenderscan.daily.plist"),
            expected_label="com.tenderscan.daily",
            expected_target_name="daily_runner.py",
            expected_schedule={"Hour": 8, "Minute": 0},
            project_dir=project_dir,
        ),
        "weekly": inspect_launchd_job(
            os.path.join(plist_dir, "com.tenderscan.weekly.plist"),
            expected_label="com.tenderscan.weekly",
            expected_target_name="weekly_report.py",
            expected_schedule={"Weekday": 2, "Hour": 9, "Minute": 0},
            project_dir=project_dir,
        ),
    }


def main() -> int:
    results = inspect_default_launchd_jobs()
    print(json.dumps(results, indent=2))
    return 0 if all(item.get("valid") for item in results.values()) else 1


if __name__ == "__main__":
    raise SystemExit(main())
