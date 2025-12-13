#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple


def _now_sast_str() -> str:
    try:
        from zoneinfo import ZoneInfo  # py3.9+

        return datetime.now(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        return (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    try:
        if isinstance(value, str) and value.strip():
            return float(value)
    except Exception:
        return None
    return None


def _get_git_sha_short(repo_root: str) -> Optional[str]:
    for key in ("GITHUB_SHA", "VERCEL_GIT_COMMIT_SHA"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val[:7]
    try:
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, text=True)
        sha = (out or "").strip()
        return sha or None
    except Exception:
        return None


def _load_payload(path: str) -> Tuple[List[dict], Dict[str, Any]]:
    with open(path, "r", encoding="utf-8") as f:
        payload = json.load(f)

    if isinstance(payload, list):
        tenders = payload
        meta: Dict[str, Any] = {}
    elif isinstance(payload, dict):
        tenders = payload.get("tenders") or payload.get("data") or []
        meta = payload.get("meta") or {}
    else:
        raise ValueError("Payload must be an array or object")

    if not isinstance(tenders, list):
        raise ValueError("Payload tenders must be an array")
    if meta and not isinstance(meta, dict):
        raise ValueError("Payload meta must be an object when present")

    # Shallow sanity
    for i, t in enumerate(tenders[:200]):
        if not isinstance(t, dict):
            raise ValueError(f"tenders[{i}] must be an object")

    return tenders, meta


def build_summary(tenders: List[dict], meta: Dict[str, Any], build_sha: Optional[str]) -> Dict[str, Any]:
    last_sync = meta.get("last_sync") or meta.get("generated_at") or _now_sast_str()
    next_run = meta.get("next_run") or "Daily 08:00"
    build_id = meta.get("build_id") or (f"{last_sync} · {build_sha}" if build_sha else last_sync)

    by_company: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    by_source: Dict[str, int] = {}

    scored = []
    for t in tenders:
        company = (t.get("company") or t.get("category") or "Unknown") or "Unknown"
        by_company[company] = by_company.get(company, 0) + 1

        source = (t.get("source") or "Unknown") or "Unknown"
        by_source[source] = by_source.get(source, 0) + 1

        scores = t.get("scores") or {}
        # Support both scoring schemas:
        priority = (scores.get("priority") or t.get("priority") or "UNKNOWN") or "UNKNOWN"
        priority = str(priority).upper()
        by_priority[priority] = by_priority.get(priority, 0) + 1

        fit = _as_number(scores.get("fit")) if "fit" in scores else _as_number(scores.get("fit_score"))
        revenue = _as_number(scores.get("revenue")) if "revenue" in scores else _as_number(scores.get("revenue_score"))
        risk = _as_number(scores.get("risk")) if "risk" in scores else _as_number(scores.get("risk_score"))

        suitability = (
            _as_number(scores.get("suitability"))
            or _as_number(scores.get("industry"))
            or _as_number(scores.get("industry_score"))
            or _as_number(scores.get("composite"))
            or _as_number(scores.get("composite_score"))
        )

        scored.append(
            (
                suitability if suitability is not None else -1.0,
                {
                    "title": t.get("title") or "-",
                    "source": source,
                    "company": company,
                    "priority": priority,
                    "close_date": t.get("closing_date") or t.get("close_date") or "-",
                    "fit": fit,
                    "revenue": revenue,
                    "risk": risk,
                    "suitability": suitability,
                    "url": t.get("url") or "",
                },
            )
        )

    scored.sort(key=lambda x: x[0], reverse=True)
    top = [row for _, row in scored[:10]]

    return {
        "generated_at": last_sync,
        "build_id": build_id,
        "build_sha": build_sha,
        "next_run": next_run,
        "counts": {
            "total": len(tenders),
            "by_company": dict(sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_priority": dict(sorted(by_priority.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "top": top,
    }


def atomic_write_json(path: str, payload: Any) -> None:
    os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
    tmp_path = path + ".tmp"
    try:
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(payload, f, ensure_ascii=False, indent=4)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
        except Exception:
            pass


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate dashboard summary.json from a tenders payload")
    parser.add_argument("--in", dest="in_path", required=True, help="Path to tenders payload (tenders-latest.json or new_tenders.json)")
    parser.add_argument("--out", dest="out_path", required=True, help="Path to write summary.json")
    parser.add_argument("--repo-root", default=os.path.dirname(os.path.dirname(os.path.abspath(__file__))), help="Repo root for git build sha")
    args = parser.parse_args()

    tenders, meta = _load_payload(args.in_path)
    build_sha = _get_git_sha_short(args.repo_root)
    summary = build_summary(tenders=tenders, meta=meta, build_sha=build_sha)
    atomic_write_json(args.out_path, summary)
    print(f"OK: wrote {args.out_path} (tenders={len(tenders)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

