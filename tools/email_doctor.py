#!/usr/bin/env python3
"""Report whether the tender digest can actually send, and optionally test it.

Usage:
    python tools/email_doctor.py           # report configuration + SMTP reachability
    python tools/email_doctor.py --send    # also send the current digest

Exit codes: 0 ok, 1 not configured, 2 send failed.

Credentials are never printed. The sender/app password are resolved exactly the
way the daily runner resolves them: environment first, then a mailctl app
password (~/.mailctl/credentials.json).
"""
from __future__ import annotations

import argparse
import os
import socket
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_DIR))

from dotenv import load_dotenv  # noqa: E402

load_dotenv(PROJECT_DIR / ".env")

from utils.email_alerts import config_status, send_daily_digest  # noqa: E402


def check_smtp(server: str, port: int, timeout: float = 8.0) -> tuple[bool, str]:
    """Open a TCP connection only; no credentials are sent."""
    try:
        with socket.create_connection((server, int(port)), timeout=timeout):
            return True, f"reachable at {server}:{port}"
    except Exception as exc:
        return False, f"{server}:{port} unreachable ({type(exc).__name__}: {exc})"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--send", action="store_true", help="send the digest after checking")
    parser.add_argument("--server", default=os.getenv("TENDERSCAN_SMTP_SERVER", "smtp.gmail.com"))
    parser.add_argument("--port", default=int(os.getenv("TENDERSCAN_SMTP_PORT", "587")), type=int)
    args = parser.parse_args()

    status = config_status()
    print("email configuration")
    print(f"  configured : {status['configured']}")
    print(f"  sender     : {status['sender'] or '<none>'}")
    print(f"  recipients : {', '.join(status['recipients']) or '<none>'}")
    if status["missing"]:
        print("  missing    :")
        for item in status["missing"]:
            print(f"    - {item}")

    reachable, detail = check_smtp(args.server, args.port)
    print(f"  smtp       : {'ok' if reachable else 'FAILED'} — {detail}")

    if not status["configured"]:
        print("\nNothing to send yet. Configure a sender and app password, e.g.:")
        print("  python3 mailctl.py gmail-add you@gmail.com")
        return 1

    if not reachable:
        return 1

    if not args.send:
        print("\nConfiguration looks usable. Re-run with --send to deliver the digest.")
        return 0

    print("\nsending digest...")
    sent = send_daily_digest()
    if sent:
        print("  sent")
        return 0
    print("  not sent — usually means no HIGH-priority tenders are pending")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
