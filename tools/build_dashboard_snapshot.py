#!/usr/bin/env python3
import argparse
import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from typing import Any, Dict, List, Optional, Tuple

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from classify_engine import classify_tender
from scoring_engine import score_tender
from scrapers.municipalities import scrape_all_municipalities
from scrapers.soes import (
    scrape_rand_water,
    scrape_transnet,
    scrape_eskom,
    scrape_sanral,
    scrape_umgeni_water,
    scrape_sasol,
    scrape_sanedi,
    scrape_anglo_american,
    scrape_harmony_gold,
    scrape_seriti,
    scrape_exxaro,
)


def _now_sast_str() -> str:
    try:
        from zoneinfo import ZoneInfo  # py3.9+

        return datetime.now(ZoneInfo("Africa/Johannesburg")).strftime("%Y-%m-%d %H:%M")
    except Exception:
        # Fallback: assume SAST = UTC+2 (no DST)
        return (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%d %H:%M")


def _today_sast_date_str() -> str:
    try:
        from zoneinfo import ZoneInfo  # py3.9+

        return datetime.now(ZoneInfo("Africa/Johannesburg")).date().isoformat()
    except Exception:
        return (datetime.utcnow() + timedelta(hours=2)).date().isoformat()

def _get_build_sha() -> Optional[str]:
    for key in ("GITHUB_SHA", "VERCEL_GIT_COMMIT_SHA"):
        val = (os.environ.get(key) or "").strip()
        if val:
            return val[:7]

    try:
        repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        out = subprocess.check_output(["git", "rev-parse", "--short", "HEAD"], cwd=repo_root, text=True)
        sha = (out or "").strip()
        return sha or None
    except Exception:
        return None


def _identity(t: dict) -> str:
    ref = (t.get("ref") or "").strip().lower()
    if ref:
        return f"ref::{ref}"
    title = (t.get("title") or "").strip().lower()
    if title:
        return f"title::{title}"
    try:
        return json.dumps(t, sort_keys=True, default=str)
    except Exception:
        return str(t)


def _as_number(value: Any) -> Optional[float]:
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return float(value)
    return None


def validate_payload(payload: Any) -> Tuple[List[dict], Dict[str, Any]]:
    if isinstance(payload, list):
        tenders = payload
        meta: Dict[str, Any] = {}
    elif isinstance(payload, dict):
        tenders = payload.get("tenders") or payload.get("data") or []
        meta = payload.get("meta") or {}
    else:
        raise ValueError("payload must be a list or object")

    if not isinstance(tenders, list):
        raise ValueError("tenders must be an array")
    if meta and not isinstance(meta, dict):
        raise ValueError("meta must be an object when present")

    for i, t in enumerate(tenders[:200]):
        if not isinstance(t, dict):
            raise ValueError(f"tender at index {i} must be an object")
        title = t.get("title")
        if title is not None and not isinstance(title, str):
            raise ValueError(f"tender[{i}].title must be a string when present")
        scores = t.get("scores")
        if scores is not None and not isinstance(scores, dict):
            raise ValueError(f"tender[{i}].scores must be an object when present")

    return tenders, meta


def atomic_write_json(path: str, payload: Any) -> None:
    directory = os.path.dirname(os.path.abspath(path))
    if directory:
        os.makedirs(directory, exist_ok=True)

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


def build_summary(meta: Dict[str, Any], tenders: List[dict]) -> Dict[str, Any]:
    by_company: Dict[str, int] = {}
    by_priority: Dict[str, int] = {}
    by_source: Dict[str, int] = {}

    scored_rows = []
    for t in tenders:
        company = (t.get("category") or t.get("company") or "Unknown") or "Unknown"
        by_company[company] = by_company.get(company, 0) + 1

        source = (t.get("source") or "Unknown") or "Unknown"
        by_source[source] = by_source.get(source, 0) + 1

        scores = t.get("scores") or {}
        priority = (scores.get("priority") or t.get("priority") or "UNKNOWN") or "UNKNOWN"
        priority = str(priority).upper()
        by_priority[priority] = by_priority.get(priority, 0) + 1

        fit = _as_number(scores.get("fit"))
        revenue = _as_number(scores.get("revenue"))
        risk = _as_number(scores.get("risk"))
        suitability = _as_number(scores.get("industry")) or _as_number(scores.get("composite"))
        scored_rows.append(
            (
                fit if fit is not None else -1.0,
                revenue if revenue is not None else -1.0,
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

    scored_rows.sort(key=lambda x: (x[0], x[1]), reverse=True)
    top = [row for _, __, row in scored_rows[:10]]

    return {
        "generated_at": meta.get("last_sync") or _now_sast_str(),
        "build_id": meta.get("build_id") or meta.get("last_sync") or _now_sast_str(),
        "build_sha": meta.get("build_sha"),
        "next_run": meta.get("next_run") or "Daily 08:00",
        "counts": {
            "total": len(tenders),
            "by_company": dict(sorted(by_company.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_priority": dict(sorted(by_priority.items(), key=lambda kv: (-kv[1], kv[0]))),
            "by_source": dict(sorted(by_source.items(), key=lambda kv: (-kv[1], kv[0]))),
        },
        "top": top,
    }


def build_snapshot(limit: int) -> dict:
    all_tenders = []

    # Keep to non-Selenium sources for CI stability
    all_tenders.extend(scrape_all_municipalities())
    soe_scrapers = [
        scrape_rand_water,
        scrape_transnet,
        scrape_eskom,
        scrape_sanral,
        scrape_umgeni_water,
        scrape_sasol,
        scrape_sanedi,
        scrape_anglo_american,
        scrape_harmony_gold,
        scrape_seriti,
        scrape_exxaro,
    ]
    for scraper in soe_scrapers:
        try:
            all_tenders.extend(scraper())
        except Exception:
            continue

    merged = []
    seen = set()
    for tender in all_tenders:
        ident = _identity(tender)
        if ident in seen:
            continue
        seen.add(ident)

        title = tender.get("title", "") or ""
        description = tender.get("description", title) or ""
        client = tender.get("client", "") or ""
        closing_date = tender.get("closing_date", "") or ""

        classification = classify_tender(title, description)
        category = classification.get("category", tender.get("category", "Unknown"))
        if category == "EXCLUDED":
            continue

        tender["category"] = category
        tender["reason"] = classification.get("reason", tender.get("reason", ""))
        tender["short_title"] = classification.get("short_title", tender.get("short_title", ""))

        tender["scores"] = score_tender(
            title=title,
            description=description,
            client=client,
            closing_date=closing_date,
            category=category,
        )

        merged.append(tender)
        if len(merged) >= limit:
            break

    last_sync = _now_sast_str()
    build_sha = _get_build_sha()

    meta: Dict[str, Any] = {
        "last_sync": last_sync,
        "next_run": "Daily 08:00",
        "build_sha": build_sha,
        "build_id": f"{last_sync} · {build_sha}" if build_sha else last_sync,
    }

    return {"meta": meta, "tenders": merged}


def render_daily_email_html(payload: Dict[str, Any], summary: Dict[str, Any], dashboard_url: str) -> str:
    meta = payload.get("meta") or {}
    tenders: List[dict] = payload.get("tenders") or []

    def esc(s: Any) -> str:
        return (
            str(s)
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
        )

    build_id = meta.get("build_id") or meta.get("last_sync") or "–"
    date_line = meta.get("last_sync") or datetime.now().strftime("%Y-%m-%d %H:%M")
    counts = (summary.get("counts") or {}) if isinstance(summary, dict) else {}
    by_priority = counts.get("by_priority") or {}
    total = counts.get("total") or len(tenders)

    # Simple prioritised list (HIGH then MEDIUM then the rest)
    def prio_key(t: dict) -> int:
        p = ((t.get("scores") or {}).get("priority") or t.get("priority") or "").upper()
        return 0 if p == "HIGH" else 1 if p == "MEDIUM" else 2 if p == "LOW" else 3

    ordered = sorted(tenders, key=lambda t: (prio_key(t), (t.get("closing_date") or "9999-99-99")))
    top_rows = ordered[:10]

    rows_html = ""
    for t in top_rows:
        scores = t.get("scores") or {}
        priority = (scores.get("priority") or t.get("priority") or "UNKNOWN").upper()
        company = t.get("category") or t.get("company") or "Unknown"
        title = (t.get("title") or "-").strip()
        source = t.get("source") or "Unknown"
        close_date = t.get("closing_date") or "-"
        url = t.get("url") or ""

        rows_html += f"""
          <tr>
            <td class="col-title">
              <div class="title">{esc(title[:160])}</div>
              <div class="meta">{esc(source)} · {esc(company)} · closes {esc(close_date)}</div>
            </td>
            <td class="col-priority">{esc(priority)}</td>
            <td class="col-scores">
              <span>Fit {esc(scores.get("fit", "-"))}</span>
              <span>Rev {esc(scores.get("revenue", "-"))}</span>
              <span>Risk {esc(scores.get("risk", "-"))}</span>
            </td>
            <td class="col-link">{f'<a href="{esc(url)}" target="_blank" rel="noopener noreferrer">View</a>' if url else '-'}</td>
          </tr>
        """

    return f"""<!doctype html>
<html>
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width,initial-scale=1" />
    <title>Tender Intelligence – Daily Email</title>
    <style>
      body {{ font-family: Arial, sans-serif; background: #f6f7fb; padding: 18px; color: #111; }}
      .container {{ max-width: 860px; margin: 0 auto; background: #fff; border-radius: 14px; padding: 18px 18px 10px; border: 1px solid rgba(0,0,0,0.06); }}
      h1 {{ margin: 0 0 2px 0; font-size: 18px; }}
      .sub {{ margin: 0 0 10px 0; color: #555; font-size: 12px; }}
      .stamp {{ margin: 0 0 12px 0; color: #666; font-size: 11px; }}
      .kpis {{ display: flex; flex-wrap: wrap; gap: 10px; margin: 10px 0 14px; }}
      .kpi {{ flex: 1 1 160px; border: 1px solid rgba(0,0,0,0.08); border-radius: 12px; padding: 10px 12px; background: #fff; }}
      .kpi .label {{ color: #666; font-size: 11px; }}
      .kpi .value {{ font-size: 18px; font-weight: 700; margin-top: 4px; }}
      table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
      th, td {{ border-top: 1px solid rgba(0,0,0,0.08); padding: 10px 8px; vertical-align: top; }}
      th {{ text-align: left; font-size: 11px; color: #555; letter-spacing: .2px; }}
      .title {{ font-weight: 700; }}
      .meta {{ color: #666; font-size: 11px; margin-top: 3px; }}
      .col-priority {{ width: 90px; font-weight: 700; }}
      .col-scores {{ width: 170px; color: #333; }}
      .col-scores span {{ display: inline-block; margin-right: 8px; }}
      .col-link {{ width: 70px; }}
      .footer {{ margin-top: 12px; padding-top: 10px; border-top: 1px solid rgba(0,0,0,0.08); color: #666; font-size: 11px; }}
    </style>
  </head>
  <body>
    <div class="container">
      <h1>Tender Intelligence – Daily Digest</h1>
      <p class="sub">TES &amp; Phakathi decision layer · {esc(date_line)}</p>
      <p class="stamp">Build stamp: <strong>{esc(build_id)}</strong></p>

      <div class="kpis">
        <div class="kpi">
          <div class="label">Total tenders</div>
          <div class="value">{esc(total)}</div>
        </div>
        <div class="kpi">
          <div class="label">High priority</div>
          <div class="value">{esc(by_priority.get("HIGH", 0))}</div>
        </div>
        <div class="kpi">
          <div class="label">Medium priority</div>
          <div class="value">{esc(by_priority.get("MEDIUM", 0))}</div>
        </div>
        <div class="kpi">
          <div class="label">Low priority</div>
          <div class="value">{esc(by_priority.get("LOW", 0))}</div>
        </div>
      </div>

      <h2 style="margin: 0 0 8px 0; font-size: 13px;">Top opportunities</h2>
      <table>
        <thead>
          <tr>
            <th>Title</th>
            <th>Priority</th>
            <th>Scores</th>
            <th>Link</th>
          </tr>
        </thead>
        <tbody>
          {rows_html}
        </tbody>
      </table>

      <div class="footer">
        Dashboard: <a href="{esc(dashboard_url)}" target="_blank" rel="noopener noreferrer">{esc(dashboard_url)}</a>
      </div>
    </div>
  </body>
</html>
"""


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Vercel dashboard tenders.json snapshot")
    parser.add_argument("--out", default="vercel-dashboard/tenders.json", help="Output path for tenders.json")
    parser.add_argument("--limit", type=int, default=200, help="Max tenders to keep in snapshot")
    parser.add_argument(
        "--public-dir",
        default="vercel-dashboard/public",
        help="Directory for versioned dashboard artifacts (tenders-latest.json, tenders-YYYY-MM-DD.json, summary.json)",
    )
    parser.add_argument(
        "--dashboard-url",
        default=os.environ.get("DASHBOARD_URL") or "https://tender-intelligence-dashboard.vercel.app/",
        help="Dashboard URL to embed in generated email artifact",
    )
    args = parser.parse_args()

    payload = build_snapshot(limit=args.limit)
    tenders, meta = validate_payload(payload)

    should_write_main = True
    if not tenders and os.path.exists(args.out):
        # Avoid wiping the dashboard if scrapes return nothing.
        # Keep the previous snapshot, but still refresh derived artifacts (summary/email)
        # to ensure downstream consumers remain consistent.
        should_write_main = False
        try:
            with open(args.out, "r", encoding="utf-8") as f:
                payload = json.load(f)
            tenders, meta = validate_payload(payload)
        except Exception:
            # If the existing snapshot is unreadable, fail hard (better than silently publishing junk).
            raise

    if should_write_main:
        atomic_write_json(args.out, payload)

    public_dir = os.path.abspath(args.public_dir)
    os.makedirs(public_dir, exist_ok=True)

    # Versioned artifacts for debugging + historical reference.
    latest_path = os.path.join(public_dir, "tenders-latest.json")
    dated_path = os.path.join(public_dir, f"tenders-{_today_sast_date_str()}.json")
    atomic_write_json(latest_path, payload)
    atomic_write_json(dated_path, payload)

    summary = build_summary(meta=meta, tenders=tenders)
    atomic_write_json(os.path.join(public_dir, "summary.json"), summary)

    # Build artifacts directory for downstream consumers (email + consistency checks).
    build_dir = os.path.join(public_dir, "build")
    os.makedirs(build_dir, exist_ok=True)
    atomic_write_json(os.path.join(build_dir, "tenders.json"), payload)
    atomic_write_json(os.path.join(build_dir, "summary.json"), summary)
    email_html = render_daily_email_html(payload=payload, summary=summary, dashboard_url=args.dashboard_url)
    tmp_email = os.path.join(build_dir, "daily_email.html.tmp")
    email_path = os.path.join(build_dir, "daily_email.html")
    try:
        with open(tmp_email, "w", encoding="utf-8") as f:
            f.write(email_html)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_email, email_path)
    finally:
        try:
            if os.path.exists(tmp_email):
                os.remove(tmp_email)
        except Exception:
            pass


if __name__ == "__main__":
    main()
