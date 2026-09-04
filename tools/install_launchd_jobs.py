#!/usr/bin/env python3
"""Safely render checkout-specific launchd plists for Tender Intelligence."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from utils.launchd_jobs import render_default_launchd_jobs, render_launchd_payloads


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Render Tender Intelligence launchd plists for this checkout."
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path.home() / "Library" / "LaunchAgents",
        help="directory for rendered plists (default: ~/Library/LaunchAgents)",
    )
    parser.add_argument(
        "--python",
        type=Path,
        default=PROJECT_DIR / ".venv" / "bin" / "python",
        help="Python executable used by daily and weekly jobs",
    )
    parser.add_argument(
        "--install",
        action="store_true",
        help="write the rendered plists; without this flag, only show the plan",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="allow replacement of existing plists (requires --install)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    python_path = args.python.expanduser().resolve()
    destination = args.output_dir.expanduser().resolve()

    if args.force and not args.install:
        raise SystemExit("--force requires --install")

    payloads = render_launchd_payloads(
        PROJECT_DIR, python_executable=python_path
    )
    if not args.install:
        print(f"Would render {len(payloads)} launchd jobs to {destination}:")
        for filename in payloads:
            print(f"  {destination / filename}")
        print("Re-run with --install after reviewing this plan.")
        return 0

    if not python_path.is_file():
        raise SystemExit(
            f"Python executable not found: {python_path}. Create .venv first or pass --python."
        )

    (PROJECT_DIR / "logs").mkdir(parents=True, exist_ok=True)
    targets = render_default_launchd_jobs(
        destination,
        PROJECT_DIR,
        python_executable=python_path,
        overwrite=args.force,
    )
    print("Rendered launchd jobs:")
    for path in targets.values():
        print(f"  {path}")
    print("Validate with plutil, then bootstrap the jobs explicitly.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
