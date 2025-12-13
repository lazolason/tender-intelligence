#!/usr/bin/env python3
import argparse
import json
import os
import sys


def _as_number(value):
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Validate dashboard tenders.json payload shape")
    parser.add_argument("--path", default="vercel-dashboard/tenders.json", help="Path to tenders.json")
    parser.add_argument(
        "--summary-path",
        default=None,
        help="Optional path to summary.json (e.g. vercel-dashboard/public/summary.json) to validate as well",
    )
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

    if meta:
        if "last_sync" in meta and not isinstance(meta["last_sync"], str):
            print("ERROR: meta.last_sync must be a string", file=sys.stderr)
            return 1
        if "next_run" in meta and not isinstance(meta["next_run"], str):
            print("ERROR: meta.next_run must be a string", file=sys.stderr)
            return 1

    # Basic sanity for tender objects (non-fatal, but useful)
    for i, t in enumerate(tenders[:200]):
        if not isinstance(t, dict):
            print(f"ERROR: tender entries must be objects; bad index: {i}", file=sys.stderr)
            return 1

        title = t.get("title")
        if title is not None and not isinstance(title, str):
            print(f"ERROR: tender[{i}].title must be a string when present", file=sys.stderr)
            return 1

        category = t.get("category")
        if category is not None and not isinstance(category, str):
            print(f"ERROR: tender[{i}].category must be a string when present", file=sys.stderr)
            return 1

        scores = t.get("scores")
        if scores is not None and not isinstance(scores, dict):
            print(f"ERROR: tender[{i}].scores must be an object when present", file=sys.stderr)
            return 1

        if isinstance(scores, dict):
            # Validate expected score types when present
            for key in ("fit", "revenue", "risk", "industry", "composite"):
                if key in scores and scores[key] is not None and _as_number(scores[key]) is None:
                    print(f"ERROR: tender[{i}].scores.{key} must be a number when present", file=sys.stderr)
                    return 1

            if "priority" in scores and scores["priority"] is not None:
                if not isinstance(scores["priority"], str):
                    print(f"ERROR: tender[{i}].scores.priority must be a string when present", file=sys.stderr)
                    return 1

    if args.summary_path:
        if not os.path.exists(args.summary_path):
            print(f"ERROR: missing file: {args.summary_path}", file=sys.stderr)
            return 1
        try:
            with open(args.summary_path, "r", encoding="utf-8") as f:
                summary = json.load(f)
        except Exception as e:
            print(f"ERROR: invalid JSON in {args.summary_path}: {e}", file=sys.stderr)
            return 1

        if not isinstance(summary, dict):
            print("ERROR: summary must be an object", file=sys.stderr)
            return 1
        if "counts" not in summary or not isinstance(summary["counts"], dict):
            print("ERROR: summary.counts must be an object", file=sys.stderr)
            return 1
        counts = summary["counts"]
        if "total" in counts and not isinstance(counts["total"], int):
            print("ERROR: summary.counts.total must be an integer", file=sys.stderr)
            return 1
        if "by_company" in counts and not isinstance(counts["by_company"], dict):
            print("ERROR: summary.counts.by_company must be an object", file=sys.stderr)
            return 1
        if "by_priority" in counts and not isinstance(counts["by_priority"], dict):
            print("ERROR: summary.counts.by_priority must be an object", file=sys.stderr)
            return 1
        if "top" in summary and not isinstance(summary["top"], list):
            print("ERROR: summary.top must be an array", file=sys.stderr)
            return 1

    print(
        f"OK: {args.path} parsed; tenders={len(tenders)}; has_meta={bool(meta)}"
        + (f"; summary={args.summary_path}" if args.summary_path else "")
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
