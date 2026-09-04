"""Render the repository's launchd templates for a specific checkout."""

from __future__ import annotations

import os
import plistlib
from pathlib import Path
from typing import Any, Dict, Mapping


PROJECT_DIR = Path(__file__).resolve().parent.parent
PROJECT_DIR_TOKEN = "__TENDERSCAN_PROJECT_DIR__"
PYTHON_TOKEN = "__TENDERSCAN_PYTHON__"
JOB_FILENAMES = (
    "com.tenderscan.app.plist",
    "com.tenderscan.daily.plist",
    "com.tenderscan.weekly.plist",
)


def _replace_tokens(value: Any, replacements: Mapping[str, str]) -> Any:
    if isinstance(value, str):
        for token, replacement in replacements.items():
            value = value.replace(token, replacement)
        return value
    if isinstance(value, list):
        return [_replace_tokens(item, replacements) for item in value]
    if isinstance(value, dict):
        return {
            _replace_tokens(key, replacements): _replace_tokens(item, replacements)
            for key, item in value.items()
        }
    return value


def default_template_paths(project_dir: str | Path = PROJECT_DIR) -> Dict[str, Path]:
    """Return the bundled launchd templates for a repository checkout."""
    root = Path(project_dir).resolve()
    return {filename: root / filename for filename in JOB_FILENAMES}


def render_launchd_payloads(
    project_dir: str | Path = PROJECT_DIR,
    *,
    python_executable: str | Path | None = None,
) -> Dict[str, Dict[str, Any]]:
    """Load templates and substitute checkout-specific runtime paths."""
    root = Path(project_dir).resolve()
    python_path = Path(python_executable or root / ".venv" / "bin" / "python").resolve()
    replacements = {
        PROJECT_DIR_TOKEN: str(root),
        PYTHON_TOKEN: str(python_path),
    }
    payloads: Dict[str, Dict[str, Any]] = {}

    for filename, template_path in default_template_paths(root).items():
        with template_path.open("rb") as file_obj:
            payload = plistlib.load(file_obj)
        rendered = _replace_tokens(payload, replacements)
        if not isinstance(rendered, dict):
            raise ValueError(f"launchd template {template_path} did not contain a plist dictionary")
        payloads[filename] = rendered

    return payloads


def render_default_launchd_jobs(
    destination_dir: str | Path,
    project_dir: str | Path = PROJECT_DIR,
    *,
    python_executable: str | Path | None = None,
    overwrite: bool = False,
) -> Dict[str, Path]:
    """Render all launchd jobs, refusing to replace files by default."""
    destination = Path(destination_dir).expanduser().resolve()
    payloads = render_launchd_payloads(
        project_dir, python_executable=python_executable
    )
    targets = {filename: destination / filename for filename in payloads}
    existing = [path for path in targets.values() if path.exists()]
    if existing and not overwrite:
        names = ", ".join(str(path) for path in existing)
        raise FileExistsError(f"refusing to overwrite existing launchd jobs: {names}")

    destination.mkdir(parents=True, exist_ok=True)
    for filename, payload in payloads.items():
        target = targets[filename]
        temporary = target.with_name(f".{target.name}.tmp")
        with temporary.open("wb") as file_obj:
            plistlib.dump(payload, file_obj, sort_keys=False)
        os.replace(temporary, target)

    return targets
