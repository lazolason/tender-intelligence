#!/usr/bin/env python3
# ==========================================================
# SYNC TENDER DATA TO LOCAL DASHBOARD
# Writes dashboard JSON consumed by the local static PWA
# ==========================================================

import json
import os
import sqlite3
from datetime import datetime
from urllib.parse import quote
import yaml
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Paths
PROJECT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.getenv("DB_PATH", os.path.join(PROJECT_DIR, "data", "tenders.db"))
DASHBOARD_DIR = os.path.join(PROJECT_DIR, "dashboard")
TENDERS_DATA_JSON = os.path.join(DASHBOARD_DIR, "tenders.json")  # Full dataset for client-side
PUBLIC_TENDERS_JSON = os.path.join(DASHBOARD_DIR, "public", "tenders-latest.json")
CONFIG_PATH = os.path.join(PROJECT_DIR, "config.yaml")

def load_config():
    """Load configuration from config.yaml."""
    try:
        with open(CONFIG_PATH, "r") as f:
            return yaml.safe_load(f) or {}
    except FileNotFoundError:
        print("⚠️ config.yaml not found, using defaults.")
    except Exception as exc:
        print(f"⚠️ Failed to read config.yaml: {exc}")
    return {}

CONFIG = load_config()
MEXEL_ONLY = bool((CONFIG.get("classification", {}) or {}).get("mexel_only", False))
COMPANIES = ["MEXEL", "PHAKATHI"]
DASHBOARD_SHOW_ALL = os.environ.get("DASHBOARD_SHOW_ALL", "").strip().lower() in ("1", "true", "yes")

# Source URLs for tender portals
SOURCE_URLS = {
    "National Treasury": "https://www.etenders.gov.za/Home/opportunities?TextSearch=",
    "Rand Water": "https://www.randwater.co.za/availabletenders.php",
    "Eskom": "https://www.eskom.co.za/eskom-tenders/",
    "Cape Town": "https://web1.capetown.gov.za/web1/TenderPortal/",
    "Transnet": "https://www.transnet.net/TenderPortal/",
    "Transnet eSupplier": "https://transnet.ebug.co.za/eBusiness/Login/",
    "Johannesburg Water SCM": "https://joburgwater.metacure.co.za/scm/tenders/",
    "Johannesburg Water": "https://www.johannesburgwater.co.za/tenders/",
    "Anglo American": "https://www.angloamerican.com/suppliers",
    "Harmony Gold": "https://www.harmony.co.za/business/procurement",
    "Seriti": "https://www.seritiza.com/procurement/",
    "SANRAL": "https://www.nra.co.za/live/tenders.php",
    "Umgeni Water": "https://umngeni-uthukela.co.za/tenders/",
    "Magalies Water": "https://magalieswater.co.za/tenders/",
    "Lepelle Northern Water": "https://lepellewater.co.za/tenders/",
    "Botswana": "https://www.etender.co.bw/",
    "Namibia": "https://www.namibiatenders.com/tenders",
}

def get_bid_statistics():
    """Get bid outcome statistics from the database."""
    try:
        with sqlite3.connect(DB_PATH) as conn:
            cursor = conn.cursor()
            
            # Total bids submitted
            cursor.execute("SELECT COUNT(*) FROM bid_outcomes WHERE bid_submitted = 1")
            total_bids = cursor.fetchone()[0]
            
            # Wins
            cursor.execute("SELECT COUNT(*) FROM bid_outcomes WHERE outcome = 'won'")
            wins = cursor.fetchone()[0]
            
            # Win rate
            win_rate = (wins / total_bids * 100) if total_bids > 0 else 0
            
            return {
                "total_bids": total_bids,
                "wins": wins,
                "win_rate": round(win_rate, 1)
            }
    except Exception as e:
        print(f"⚠️ Failed to get bid statistics: {e}")
        return {"total_bids": 0, "wins": 0, "win_rate": 0}

def load_planned_opportunities():
    """Load relevant Treasury procurement plans for the dashboard pipeline view."""
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        table_exists = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type='table' AND name='planned_opportunities'"
        ).fetchone()
        if not table_exists:
            return []
        rows = conn.execute(
            """
            SELECT external_id, institution, description, planned_advert_date,
                   planned_closing_date, planned_award_date, category,
                   classification_reason, matched_keywords, lifecycle_stage,
                   source, source_url, matched_tender_ref, is_active, retired_at,
                   first_seen_at, last_seen_at
            FROM planned_opportunities
            WHERE is_active = 1
              AND category IN ('MEXEL', 'PHAKATHI')
              AND lifecycle_stage IN ('PLANNED', 'DUE_SOON', 'OVERDUE')
            ORDER BY
                CASE WHEN planned_advert_date IS NULL THEN 1 ELSE 0 END,
                planned_advert_date ASC
            """
        ).fetchall()

    plans = []
    for row in rows:
        plan = dict(row)
        try:
            plan["matched_keywords"] = json.loads(plan.get("matched_keywords") or "[]")
        except (TypeError, ValueError, json.JSONDecodeError):
            plan["matched_keywords"] = []
        plan["company"] = {"MEXEL": "Mexel", "PHAKATHI": "Phakathi"}.get(
            plan.get("category"), "Unknown"
        )
        plans.append(plan)
    return plans


def load_tenders():
    """Load tenders from SQLite database with PDF analysis."""
    tenders = []
    
    with sqlite3.connect(DB_PATH) as conn:
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        # Get all relevant tenders with LEFT JOIN to pdf_analysis
        query = """
            SELECT t.*, 
                   p.page_count, p.word_count, p.requirements, p.deadlines, 
                   p.values_extracted, p.contact_info
            FROM tenders t
            LEFT JOIN pdf_analysis p ON t.ref = p.tender_ref
            WHERE t.status IN ('Open', 'Active', 'In Progress')
        """
        if MEXEL_ONLY and not DASHBOARD_SHOW_ALL:
            query += " AND t.category = 'MEXEL'"
        elif not DASHBOARD_SHOW_ALL:
            query += " AND t.category IN ('MEXEL', 'PHAKATHI')"
        
        query += " ORDER BY t.created_at DESC"
        
        cursor.execute(query)
        rows = cursor.fetchall()
        
        for row in rows:
            t = dict(row)
            # Reconstruct the scores dict for compatibility with existing dashboard code
            t["scores"] = {
                "composite_score": t.get("composite_score", 0),
                "fit_score": t.get("fit_score", 0),
                "mexel_suitability": t.get("mexel_suitability", 0),
                "priority": t.get("priority", "LOW")
            }
            # Add type for backward compatibility
            t["type"] = t.get("category", "Unknown")
            
            # Parse PDF analysis JSON fields if present
            if t.get("requirements"):
                try:
                    t["requirements"] = json.loads(t["requirements"])
                except:
                    t["requirements"] = []
            if t.get("deadlines"):
                try:
                    t["deadlines"] = json.loads(t["deadlines"])
                except:
                    t["deadlines"] = []
            if t.get("values_extracted"):
                try:
                    t["values_extracted"] = json.loads(t["values_extracted"])
                except:
                    t["values_extracted"] = []
            if t.get("contact_info"):
                try:
                    t["contact_info"] = json.loads(t["contact_info"])
                except:
                    t["contact_info"] = {}
            
            tenders.append(t)
            
    return tenders, {"db_count": len(tenders)}

def is_mexel_tender(tender):
    """Filter to relevant tenders using multi-signal checks."""
    category = (tender.get("category") or "").strip().upper()
    tender_type = (tender.get("type") or tender.get("tender_type") or "").strip().upper()
    if category in ("MEXEL", "PHAKATHI") or tender_type in ("MEXEL", "PHAKATHI"):
        return True
    scores = tender.get("scores", {}) or {}
    for value in (
        scores.get("mexel_suitability"),
        scores.get("mexel_score"),
        scores.get("mexel_fit"),
        tender.get("mexel_suitability"),
        tender.get("mexel_score"),
        tender.get("mexel_fit"),
    ):
        try:
            if value is not None and float(value) > 0:
                return True
        except (TypeError, ValueError):
            continue
    return False

def get_search_url(tender):
    """Generate a search URL for the tender"""
    source = tender.get("source", "")
    ref = tender.get("ref", "")
    title = tender.get("title", "")
    
    if "treasury" in source.lower() or source.startswith("NT"):
        search_term = ref if ref and not ref.startswith("NT-") else title[:50]
        return f"https://www.etenders.gov.za/Home/opportunities?TextSearch={quote(search_term)}"
    
    if source in SOURCE_URLS:
        return SOURCE_URLS[source]
    
    search_query = f"{ref} {title[:40]} tender site:gov.za"
    return f"https://www.google.com/search?q={quote(search_query)}"


def write_dashboard_payload(payload, *, output_paths=None):
    """Write the dashboard payload to all configured snapshot locations."""
    paths = list(output_paths or [TENDERS_DATA_JSON, PUBLIC_TENDERS_JSON])
    for path in paths:
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as file_obj:
            json.dump(payload, file_obj, indent=2)
    return paths

def sync():
    """Write the latest dashboard payload from SQLite to `dashboard/tenders.json`."""
    print("🔄 Syncing tender data to local dashboard...")
    
    tenders, stats = load_tenders()
    planned_opportunities = load_planned_opportunities()
    scraped_count = len(tenders)
    print(f"   Found {scraped_count} tenders in database")
    print(f"   Found {len(planned_opportunities)} relevant planned opportunities")
    
    metadata = {
        "meta": {
            "last_sync": datetime.now().strftime("%Y-%m-%d %H:%M"),
            "snapshot_origin": "local_database",
            "next_run": "Daily 08:00",
            "tender_count": len(tenders),
            "last_update": datetime.now().isoformat(),
            "planned_opportunity_count": len(planned_opportunities)
        },
        "tenders": tenders
    }
    
    # Get bid statistics
    bid_stats = get_bid_statistics()
    
    # Re-map tenders for dashboard compatibility
    js_tenders = []
    for t in tenders:
        url = t.get("url", "") or get_search_url(t)
        
        # Parse matched_keywords if it's a string
        matched_keywords = t.get("matched_keywords", "")
        if isinstance(matched_keywords, str):
            matched_keywords = [kw.strip() for kw in matched_keywords.split(",") if kw.strip()]
        elif not matched_keywords:
            matched_keywords = []

        category_display = t.get("category", "Unknown")
        company_map = {"MEXEL": "Mexel", "PHAKATHI": "Phakathi"}
        category = company_map.get(category_display, category_display)
        company = company_map.get(category_display, "Unknown")

        tender_data = {
            "ref": t.get("ref", "N/A"),
            "title": t.get("title", "Unknown"),
            "description": t.get("description", t.get("title", "")),
            "client": t.get("client", "Unknown"),
            "priority": t.get("priority", "LOW"),
            "score": t.get("composite_score", 0),
            "category": category,
            "source": t.get("source", "Unknown"),
            "url": url,
            "company": company,
            "closing_date": t.get("closing_date", ""),
            "matched_keywords": matched_keywords
        }
        
        # Add PDF analysis if available
        if t.get("page_count"):
            tender_data["pdf_analysis"] = {
                "page_count": t.get("page_count"),
                "word_count": t.get("word_count"),
                "requirements": t.get("requirements", []),
                "deadlines": t.get("deadlines", []),
                "values": t.get("values_extracted", []),
                "contact": t.get("contact_info", {})
            }
        
        js_tenders.append(tender_data)

    # Update metadata with bid statistics
    metadata["meta"]["bid_statistics"] = bid_stats
    
    payload = {
        "meta": metadata["meta"],
        "tenders": js_tenders,
        "planned_opportunities": planned_opportunities,
    }
    write_dashboard_payload(payload)

    print(f"   ✅ Dashboard data file (tenders.json) updated")
    print(f"   ✅ Public dashboard snapshot (public/tenders-latest.json) updated")
    print(f"   📊 Bid Statistics: {bid_stats['wins']}/{bid_stats['total_bids']} wins ({bid_stats['win_rate']}%)")
    
    return True

if __name__ == "__main__":
    sync()
