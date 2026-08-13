#!/usr/bin/env python3
"""Import an explicitly allowlisted licensed/authorized local tender export."""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.authorized_feed import AuthorizedFeedError, ingest_authorized_feed
from utils.config_validator import load_and_validate_config


PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Import an approved JSON/CSV export from the confined feed inbox"
    )
    parser.add_argument("--source", required=True, help="Allowlisted source id from config.yaml")
    parser.add_argument("--file", required=True, help="File name/path inside authorized_feeds.inbox_dir")
    parser.add_argument("--dry-run", action="store_true", help="Validate and classify without persistence")
    args = parser.parse_args()

    config = load_and_validate_config(os.path.join(PROJECT_DIR, "config.yaml"))
    feed_config = config.get("authorized_feeds") or {}
    inbox = feed_config.get("inbox_dir", "data/authorized_feeds/inbox")
    if not os.path.isabs(inbox):
        feed_config["inbox_dir"] = os.path.join(PROJECT_DIR, inbox)

    db_path = os.getenv("DB_PATH", os.path.join(PROJECT_DIR, "data", "tenders.db"))
    try:
        result = ingest_authorized_feed(
            config=config,
            source_id=args.source,
            file_path=args.file,
            db_path=db_path,
            dry_run=args.dry_run,
        )
    except (AuthorizedFeedError, FileNotFoundError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2
    except Exception as exc:
        print(
            json.dumps({"status": "error", "error": type(exc).__name__}, indent=2),
            file=sys.stderr,
        )
        return 1

    print(json.dumps(result, indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
