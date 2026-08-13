import os
import shutil
import subprocess
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent


def _pytest_args():
    return ["-v", "-p", "no:cov", "-p", "no:hydra-core", "tests"]


def _current_python_has_pytest() -> bool:
    try:
        import pytest  # type: ignore
        return True
    except ModuleNotFoundError:
        return False


def _python_executable_has_pytest(python_executable: Path) -> bool:
    proc = subprocess.run(
        [str(python_executable), "-c", "import pytest"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def _python_executable_has_module(python_executable: Path, module_name: str) -> bool:
    proc = subprocess.run(
        [str(python_executable), "-c", f"import {module_name}"],
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    return proc.returncode == 0


def _find_python_for_pytest() -> Path | None:
    if _current_python_has_pytest():
        return Path(sys.executable)

    for venv_name in (".venv", ".venv-verify", ".venv-test"):
        venv_python = REPO_ROOT / venv_name / "bin" / "python"
        if venv_python.exists() and _python_executable_has_pytest(venv_python):
            return venv_python

    return None


def _run_python_tests() -> int:
    python_executable = _find_python_for_pytest()
    if python_executable is None:
        print(
            "pytest is not available and no supported repo virtualenv was found "
            "(.venv, .venv-verify, .venv-test)."
        )
        return 1

    print(f"[python] using {python_executable}")
    proc = subprocess.run(
        [str(python_executable), "-m", "pytest", *_pytest_args()],
        cwd=REPO_ROOT,
    )
    return proc.returncode


def _find_python_for_flask_smoke() -> Path | None:
    candidates = [
        Path(sys.executable),
        REPO_ROOT / ".venv" / "bin" / "python",
        REPO_ROOT / ".venv-verify" / "bin" / "python",
        REPO_ROOT / ".venv-test" / "bin" / "python",
    ]

    seen = set()
    for candidate in candidates:
        if not candidate or candidate in seen:
            continue
        seen.add(candidate)
        if candidate.exists() and _python_executable_has_module(candidate, "flask"):
            return candidate

    system_python = shutil.which("python3")
    if system_python:
        system_path = Path(system_python)
        if _python_executable_has_module(system_path, "flask"):
            return system_path

    return None


def _run_flask_dashboard_smoke() -> int:
    python_executable = _find_python_for_flask_smoke()
    if python_executable is None:
        print("[flask-smoke] skipped: no Python interpreter with Flask is available")
        return 0

    print(f"[flask-smoke] using {python_executable}")
    script = """
import json
from app import app

client = app.test_client()
root = client.get("/")
assert root.status_code == 200, root.status_code
assert b"Tender Intelligence Dashboard" in root.data

payload = client.get("/tenders.json")
assert payload.status_code == 200, payload.status_code
body = json.loads(payload.data)
assert isinstance(body.get("tenders"), list)

health = client.get("/health")
assert health.status_code in {200, 503}, health.status_code
print("flask dashboard smoke passed")
"""
    proc = subprocess.run([str(python_executable), "-c", script], cwd=REPO_ROOT)
    return proc.returncode


def _run_dashboard_checks() -> int:
    dashboard_dir = REPO_ROOT / "dashboard"
    if not dashboard_dir.exists():
        print("[dashboard] skipped: dashboard directory not found")
        return 0

    npm = shutil.which("npm")
    if npm is None:
        print("[dashboard] skipped: npm is not installed")
        return 0

    commands = [
        ("lint", [npm, "run", "lint"]),
        ("test", [npm, "run", "test:run"]),
        ("smoke", [npm, "run", "test:smoke"]),
    ]

    for label, cmd in commands:
        print(f"[dashboard] running {label}")
        proc = subprocess.run(cmd, cwd=dashboard_dir)
        if proc.returncode != 0:
            return proc.returncode

    return 0


# Add project root to sys.path
sys.path.insert(0, os.path.abspath(REPO_ROOT))

if __name__ == "__main__":
    python_status = _run_python_tests()
    flask_smoke_status = _run_flask_dashboard_smoke() if python_status == 0 else 0
    dashboard_status = _run_dashboard_checks() if (python_status == 0 and flask_smoke_status == 0) else 0
    sys.exit(python_status or flask_smoke_status or dashboard_status)
