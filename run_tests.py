import sys
import os
import subprocess
from pathlib import Path


def _pytest_args():
    return ["-v", "-p", "no:cov", "-p", "no:hydra-core", "tests"]


def _run_with_venv_python() -> int:
    repo_root = Path(__file__).resolve().parent
    venv_python = repo_root / ".venv" / "bin" / "python"
    if not venv_python.exists():
        print("pytest is not installed in the current interpreter and .venv Python was not found.")
        return 1
    proc = subprocess.run([str(venv_python), "-m", "pytest", *_pytest_args()], cwd=repo_root)
    return proc.returncode

# Add project root to sys.path
sys.path.insert(0, os.path.abspath(os.path.dirname(__file__)))

if __name__ == "__main__":
    try:
        import pytest  # type: ignore
        sys.exit(pytest.main(_pytest_args()))
    except ModuleNotFoundError:
        sys.exit(_run_with_venv_python())
