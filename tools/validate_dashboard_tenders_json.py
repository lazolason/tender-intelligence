#!/usr/bin/env python3
import argparse
import json
import os
import sys


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dashboard tenders.json payload shape")
    parser.add_argument("--path", default="vercel-dashboard/tenders.json", help="Path to tenders.json")
    args = parser.parse_args()

    if not os.path.exists(args.path):
        print(f"ERROR: missing file: {args.path}", file=sys.stderr)
        return 1

    try:
        with open(args.path, "r", encoding="utf-8") as f:
            payload = json.load(f)
    except Exception as e:
        print(f"ERROR: invalid JSON in {args.path}: {e}", file=sys.stderr)
        return 1

    if isinstance(payload, list):
        tenders = payload
        meta = {}
    elif isinstance(payload, dict):
        tenders = payload.get("tenders") or payload.get("data") or []
        meta = payload.get("meta") or {}
    else:
        print("ERROR: payload must be a list or object", file=sys.stderr)
        return 1

    if not isinstance(tenders, list):
        print("ERROR: tenders must be an array", file=sys.stderr)
        return 1

    if meta and not isinstance(meta, dict):
        print("ERROR: meta must be an object when present", file=sys.stderr)
        return 1

    # Basic sanity for tender objects (non-fatal, but useful)
    bad = [i for i, t in enumerate(tenders[:50]) if not isinstance(t, dict)]
    if bad:
        print(f"ERROR: tender entries must be objects; bad indices: {bad[:10]}", file=sys.stderr)
        return 1

    print(f"OK: {args.path} parsed; tenders={len(tenders)}; has_meta={bool(meta)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

