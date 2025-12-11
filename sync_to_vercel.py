#!/usr/bin/env python3
# ==========================================================
# SYNC TENDER DATA TO VERCEL DASHBOARD
# Updates HTML and pushes to GitHub (triggers Vercel auto-deploy)
# ==========================================================

import json
import os
import subprocess
from datetime import datetime, timedelta
from urllib.parse import quote

# Paths
AUTOMATION_DIR = os.path.dirname(os.path.abspath(__file__))
# Tenders are written to MASTER folder by tenderscan.py (see config.yaml)
OUTPUT_DIR = "/Users/lazolasonqishe/Documents/MASTER/TENDERS/00_System/04_Automation/output"
# Vercel dashboard is in the MASTER folder (separate git repo: lazolason/tender-dashboard)
VERCEL_DIR = "/Users/lazolasonqishe/Documents/MASTER/TENDERS/00_System/04_Automation/vercel-dashboard"
TENDERS_JSON = os.path.join(OUTPUT_DIR, "new_tenders.json")
DASHBOARD_HTML = os.path.join(VERCEL_DIR, "index.html")

# Source URLs for tender portals
SOURCE_URLS = {
    "National Treasury": "https://www.etenders.gov.za/Home/opportunities?TextSearch=",
    "Rand Water": "https://www.randwater.co.za/availabletenders.php",
    "Eskom": "https://www.eskom.co.za/eskom-tenders/",
    "Ekurhuleni": "https://www.ekurhuleni.gov.za/scm-tenders",
    "Tshwane": "https://www.tshwane.gov.za/sites/Departments/Financial-Services/Pages/Tenders.aspx",
    "Cape Town": "https://web1.capetown.gov.za/web1/TenderPortal/",
    "eThekwini": "https://www.durban.gov.za/pages/government/scm/tenders.aspx",
    "Transnet": "https://www.transnet.net/TenderPortal/",
    "Johannesburg Water": "https://www.johannesburgwater.co.za/tenders/",
    "Umgeni Water": "https://www.umgeni.co.za/tenders/",
    "Sasol": "https://www.sasol.com/procurement",
    "SANEDI": "https://www.sanedi.org.za/tenders/",
    "Anglo American": "https://www.angloamerican.com/suppliers",
    "Harmony Gold": "https://www.harmony.co.za/business/procurement",
    "Seriti": "https://www.seritiza.com/procurement/",
    "Exxaro": "https://www.exxaro.com/suppliers/",
    "SANRAL": "https://www.nra.co.za/live/tenders.php",
}

def load_tenders():
    """Load tenders from JSON output"""
    if os.path.exists(TENDERS_JSON):
        with open(TENDERS_JSON, "r") as f:
            return json.load(f)
    return []

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

def generate_dashboard_html(tenders):
    """Generate updated dashboard HTML with real tender data"""
    
    total = len(tenders)
    high = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "HIGH")
    medium = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "MEDIUM")
    low = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "LOW")
    
    tes_count = sum(1 for t in tenders if t.get("scores", {}).get("tes_suitability", 0) > t.get("scores", {}).get("phakathi_suitability", 0))
    phakathi_count = sum(1 for t in tenders if t.get("scores", {}).get("phakathi_suitability", 0) > t.get("scores", {}).get("tes_suitability", 0))
    both_count = total - tes_count - phakathi_count
    
    # Priority counts
    high_count = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "HIGH")
    medium_count = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "MEDIUM")
    low_count = sum(1 for t in tenders if t.get("scores", {}).get("priority") == "LOW")
    
    js_tenders = []
    for t in tenders[:20]:
        scores = t.get("scores", {})
        tes_score = scores.get("tes_suitability", 0)
        phakathi_score = scores.get("phakathi_suitability", 0)
        
        if tes_score > phakathi_score:
            company = "TES"
        elif phakathi_score > tes_score:
            company = "Phakathi"
        else:
            company = "Both"
        
        url = t.get("url", "") or get_search_url(t)
        
        # Get PDF file size if available
        pdf_size = t.get("pdf_size", "")
        if not pdf_size and url.endswith('.pdf'):
            # Quick attempt to get size from headers
            try:
                import urllib.request
                req = urllib.request.Request(url, method='HEAD')
                response = urllib.request.urlopen(req, timeout=3)
                size_bytes = int(response.headers.get('content-length', 0))
                if size_bytes > 0:
                    for unit in ['B', 'KB', 'MB']:
                        if size_bytes < 1024:
                            pdf_size = f"{size_bytes} {unit}" if unit == 'B' else f"{size_bytes:.1f} {unit}"
                            break
                        size_bytes /= 1024.0
            except:
                pass
        
        js_tenders.append({
            "ref": t.get("ref", "N/A"),
            "title": t.get("title", "Unknown"),
            "description": t.get("description", t.get("title", "")),
            "client": t.get("client", "Unknown"),
            "priority": scores.get("priority", "LOW"),
            "score": scores.get("composite_score", 0),
            "category": t.get("category", "Unknown"),
            "source": t.get("source", "Unknown"),
            "url": url,
            "pdf_size": pdf_size,
            "company": company,
            "tes_score": tes_score,
            "phakathi_score": phakathi_score,
            "closing_date": t.get("closing_date", ""),
            "contact": t.get("contact", "")
        })
    
    tenders_json = json.dumps(js_tenders, indent=8)
    last_updated = datetime.now().strftime("%d %b %Y, %H:%M")
    
    html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <meta name="apple-mobile-web-app-capable" content="yes">
    <meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
    <link rel="manifest" href="manifest.json">
    <title>Tender Intelligence Dashboard</title>
    <style>
        * {{ margin: 0; padding: 0; box-sizing: border-box; }}
        body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif; background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); color: #fff; min-height: 100vh; padding: 20px; }}
        .container {{ max-width: 1400px; margin: 0 auto; }}
        header {{ text-align: center; padding: 40px 0; }}
        h1 {{ font-size: 3rem; margin-bottom: 10px; background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); -webkit-background-clip: text; -webkit-text-fill-color: transparent; }}
        .subtitle {{ color: #888; font-size: 1.1rem; }}
        .status {{ display: inline-block; width: 12px; height: 12px; border-radius: 50%; background: #00ff88; margin-right: 8px; animation: pulse 2s infinite; }}
        @keyframes pulse {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.5; }} }}
        .last-sync {{ display: inline-block; background: rgba(102, 126, 234, 0.2); color: #667eea; padding: 8px 16px; border-radius: 20px; font-size: 0.85rem; margin-top: 15px; border: 1px solid rgba(102, 126, 234, 0.3); }}
        
        /* Tab Navigation */
        .tab-nav {{ display: flex; justify-content: center; gap: 10px; margin: 30px 0; flex-wrap: wrap; }}
        .tab-btn {{ padding: 12px 24px; border-radius: 25px; border: 1px solid rgba(255,255,255,0.2); background: transparent; color: #888; cursor: pointer; transition: all 0.3s; font-size: 0.9rem; font-weight: 500; }}
        .tab-btn:hover {{ border-color: rgba(255,255,255,0.4); color: #fff; }}
        .tab-btn.active {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); border-color: transparent; color: #fff; }}
        .tab-content {{ display: none; }}
        .tab-content.active {{ display: block; }}
        
        /* Stats */
        .stats {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr)); gap: 15px; margin: 30px 0; }}
        .stat-card {{ background: rgba(255,255,255,0.05); backdrop-filter: blur(10px); border-radius: 20px; padding: 25px; border: 1px solid rgba(255,255,255,0.1); text-align: center; transition: transform 0.3s; }}
        .stat-card:hover {{ transform: translateY(-5px); box-shadow: 0 20px 40px rgba(0,0,0,0.3); }}
        .stat-value {{ font-size: 2.5rem; font-weight: 700; margin-bottom: 10px; }}
        .stat-label {{ color: #888; text-transform: uppercase; letter-spacing: 1px; font-size: 0.75rem; }}
        .high {{ color: #ff6b6b; }} .medium {{ color: #feca57; }} .low {{ color: #48dbfb; }} .total {{ color: #a29bfe; }}
        .tes-color {{ color: #48dbfb; }} .phakathi-color {{ color: #feca57; }}
        
        /* Sections */
        .section {{ background: rgba(255,255,255,0.03); border-radius: 20px; padding: 30px; margin: 30px 0; border: 1px solid rgba(255,255,255,0.05); }}
        .section h2 {{ margin-bottom: 20px; color: #fff; }}
        
        /* Tender List */
        .tender-list {{ list-style: none; }}
        .tender-item {{ padding: 20px; border-bottom: 1px solid rgba(255,255,255,0.05); transition: all 0.2s; cursor: pointer; border-left: 4px solid transparent; }}
        .tender-item:hover {{ background: rgba(255,255,255,0.08); }}
        .tender-item.urgent {{ border-left: 4px solid #ff6b6b; background: linear-gradient(135deg, rgba(255,107,107,0.1) 0%, transparent 100%); }}
        .tender-item.warning {{ border-left: 4px solid #feca57; background: linear-gradient(135deg, rgba(254,202,87,0.08) 0%, transparent 100%); }}
        .tender-content {{ display: flex; justify-content: space-between; align-items: flex-start; flex-wrap: wrap; gap: 15px; }}
        .tender-info {{ flex: 1; min-width: 250px; }}
        .tender-header {{ display: flex; align-items: center; gap: 10px; flex-wrap: wrap; margin-bottom: 8px; }}
        .tender-ref {{ color: #667eea; font-weight: 600; font-size: 1.1rem; }}
        .tender-title {{ color: #fff; font-size: 1rem; font-weight: 600; line-height: 1.4; margin-bottom: 8px; }}
        .tender-description {{ color: #999; font-size: 0.9rem; line-height: 1.5; margin-bottom: 10px; padding: 10px; background: rgba(255,255,255,0.03); border-radius: 8px; border-left: 3px solid #667eea; }}
        .tender-meta {{ color: #666; font-size: 0.8rem; display: flex; flex-wrap: wrap; gap: 15px; }}
        
        /* Badges */
        .company-badge {{ padding: 4px 12px; border-radius: 15px; font-size: 0.7rem; font-weight: 700; text-transform: uppercase; letter-spacing: 1px; }}
        .company-TES {{ background: rgba(72, 219, 251, 0.2); color: #48dbfb; border: 1px solid rgba(72, 219, 251, 0.4); }}
        .company-Phakathi {{ background: rgba(254, 202, 87, 0.2); color: #feca57; border: 1px solid rgba(254, 202, 87, 0.4); }}
        .company-Both {{ background: rgba(162, 155, 254, 0.2); color: #a29bfe; border: 1px solid rgba(162, 155, 254, 0.4); }}
        .priority-badge {{ padding: 8px 16px; border-radius: 25px; font-size: 0.75rem; font-weight: 700; }}
        .priority-HIGH {{ background: rgba(255, 107, 107, 0.2); color: #ff6b6b; }}
        .priority-MEDIUM {{ background: rgba(254, 202, 87, 0.2); color: #feca57; }}
        .priority-LOW {{ background: rgba(72, 219, 251, 0.2); color: #48dbfb; }}
        
        /* Countdown Badge */
        .countdown {{ padding: 4px 10px; border-radius: 12px; font-size: 0.7rem; font-weight: 600; }}
        .countdown.urgent {{ background: rgba(255, 107, 107, 0.3); color: #ff6b6b; animation: blink 1s infinite; }}
        .countdown.warning {{ background: rgba(254, 202, 87, 0.3); color: #feca57; }}
        .countdown.normal {{ background: rgba(72, 219, 251, 0.2); color: #48dbfb; }}
        .countdown.closed {{ background: rgba(100, 100, 100, 0.3); color: #888; text-decoration: line-through; }}
        @keyframes blink {{ 0%, 100% {{ opacity: 1; }} 50% {{ opacity: 0.6; }} }}
        
        .tender-right {{ display: flex; align-items: center; gap: 15px; }}
        .score {{ font-size: 1.8rem; font-weight: 700; min-width: 50px; text-align: center; }}
        .view-btn {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 10px 20px; border-radius: 25px; text-decoration: none; font-size: 0.85rem; font-weight: 600; display: inline-flex; align-items: center; gap: 8px; transition: transform 0.2s, box-shadow 0.2s; }}
        .view-btn:hover {{ transform: scale(1.05); box-shadow: 0 5px 20px rgba(102, 126, 234, 0.4); }}
        
        /* Calendar */
        .calendar {{ display: grid; grid-template-columns: repeat(7, 1fr); gap: 5px; }}
        .calendar-header {{ text-align: center; padding: 10px; color: #888; font-size: 0.8rem; font-weight: 600; }}
        .calendar-day {{ aspect-ratio: 1; display: flex; flex-direction: column; align-items: center; justify-content: center; border-radius: 10px; background: rgba(255,255,255,0.03); font-size: 0.9rem; position: relative; cursor: pointer; transition: all 0.2s; }}
        .calendar-day:hover {{ background: rgba(255,255,255,0.1); }}
        .calendar-day.today {{ border: 2px solid #667eea; }}
        .calendar-day.other-month {{ opacity: 0.3; }}
        .calendar-day.has-tenders {{ background: rgba(255, 107, 107, 0.2); }}
        .calendar-day.has-tenders:hover {{ background: rgba(255, 107, 107, 0.3); }}
        .tender-dot {{ width: 6px; height: 6px; border-radius: 50%; background: #ff6b6b; position: absolute; bottom: 5px; }}
        .tender-count {{ font-size: 0.6rem; color: #ff6b6b; margin-top: 2px; }}
        .calendar-nav {{ display: flex; justify-content: space-between; align-items: center; margin-bottom: 20px; }}
        .calendar-nav button {{ background: rgba(255,255,255,0.1); border: none; color: #fff; padding: 10px 20px; border-radius: 10px; cursor: pointer; }}
        .calendar-nav button:hover {{ background: rgba(255,255,255,0.2); }}
        .calendar-month {{ font-size: 1.2rem; font-weight: 600; }}
        
        /* Company Cards */
        .companies {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(250px, 1fr)); gap: 20px; margin-top: 20px; }}
        .company-card {{ background: linear-gradient(135deg, rgba(102,126,234,0.1) 0%, rgba(118,75,162,0.1) 100%); border-radius: 16px; padding: 25px; border: 1px solid rgba(102,126,234,0.3); }}
        .company-name {{ font-size: 1.3rem; font-weight: 700; margin-bottom: 10px; }}
        .company-focus {{ color: #888; font-size: 0.9rem; }}
        .company-keywords {{ margin-top: 15px; }}
        .keyword {{ display: inline-block; background: rgba(255,255,255,0.1); padding: 5px 12px; border-radius: 15px; font-size: 0.75rem; margin: 3px; color: #aaa; }}
        
        /* Filter Tabs */
        .filter-tabs {{ display: flex; gap: 10px; margin-bottom: 20px; flex-wrap: wrap; }}
        .filter-tab {{ padding: 10px 20px; border-radius: 25px; border: 1px solid rgba(255,255,255,0.2); background: transparent; color: #888; cursor: pointer; transition: all 0.2s; font-size: 0.85rem; }}
        .filter-tab:hover {{ border-color: rgba(255,255,255,0.4); color: #fff; }}
        .filter-tab.active {{ background: rgba(102, 126, 234, 0.3); border-color: #667eea; color: #fff; }}
        .filter-tab.high {{ border-left: 3px solid #ff6b6b; }}
        .filter-tab.medium {{ border-left: 3px solid #ffc107; }}
        .filter-tab.low {{ border-left: 3px solid #17a2b8; }}
        .filter-tab.high.active {{ background: linear-gradient(135deg, rgba(255,107,107,0.3), rgba(238,90,90,0.3)); border-color: #ff6b6b; }}
        .filter-tab.medium.active {{ background: linear-gradient(135deg, rgba(255,193,7,0.3), rgba(224,168,0,0.3)); border-color: #ffc107; }}
        .filter-tab.low.active {{ background: linear-gradient(135deg, rgba(23,162,184,0.3), rgba(19,132,150,0.3)); border-color: #17a2b8; }}
        
        .footer {{ text-align: center; padding: 40px; color: #444; font-size: 0.85rem; }}
        .empty-state {{ text-align: center; padding: 60px; color: #666; }}
        
        /* Tooltip */
        .tooltip {{ position: absolute; background: #1a1a2e; border: 1px solid rgba(255,255,255,0.2); padding: 10px 15px; border-radius: 10px; font-size: 0.8rem; z-index: 100; white-space: nowrap; display: none; }}
        
        @media (max-width: 768px) {{ 
            h1 {{ font-size: 2rem; }} 
            .stat-value {{ font-size: 1.8rem; }} 
            .tender-content {{ flex-direction: column; align-items: flex-start; }} 
            .tender-right {{ margin-top: 15px; width: 100%; justify-content: space-between; }}
            .calendar {{ grid-template-columns: repeat(7, 1fr); gap: 2px; }}
            .calendar-day {{ font-size: 0.75rem; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <header>
            <h1>🎯 Tender Intelligence</h1>
            <p class="subtitle"><span class="status"></span>TES & Phakathi Automation Engine</p>
            <div class="last-sync">🔄 Last synced: {last_updated}</div>
        </header>
        
        <nav class="tab-nav">
            <button class="tab-btn active" onclick="showTab('dashboard')">📊 Dashboard</button>
            <button class="tab-btn" onclick="showTab('calendar')">📅 Bid Calendar</button>
            <button class="tab-btn" onclick="showTab('sources')">�� Sources</button>
        </nav>
        
        <!-- DASHBOARD TAB -->
        <div id="dashboard" class="tab-content active">
            <div class="stats">
                <div class="stat-card"><div class="stat-value total">{total}</div><div class="stat-label">Total</div></div>
                <div class="stat-card"><div class="stat-value high">{high}</div><div class="stat-label">🔥 High</div></div>
                <div class="stat-card"><div class="stat-value medium">{medium}</div><div class="stat-label">✅ Medium</div></div>
                <div class="stat-card"><div class="stat-value low">{low}</div><div class="stat-label">📝 Low</div></div>
                <div class="stat-card"><div class="stat-value tes-color">{tes_count}</div><div class="stat-label">💧 TES</div></div>
                <div class="stat-card"><div class="stat-value phakathi-color">{phakathi_count}</div><div class="stat-label">⚙️ Phakathi</div></div>
            </div>
            
            <div class="section">
                <h2>📋 Active Tenders</h2>
                <div class="filter-tabs">
                    <button class="filter-tab active" onclick="filterTenders('all')">All ({total})</button>
                    <button class="filter-tab" onclick="filterTenders('TES')">💧 TES ({tes_count})</button>
                    <button class="filter-tab" onclick="filterTenders('Phakathi')">⚙️ Phakathi ({phakathi_count})</button>
                    <button class="filter-tab high" onclick="filterTenders('HIGH')">🔥 HIGH ({high_count})</button>
                    <button class="filter-tab medium" onclick="filterTenders('MEDIUM')">⚡ MEDIUM ({medium_count})</button>
                    <button class="filter-tab low" onclick="filterTenders('LOW')">📝 LOW ({low_count})</button>
                </div>
                <ul class="tender-list" id="tenderList"></ul>
            </div>
        </div>
        
        <!-- CALENDAR TAB -->
        <div id="calendar" class="tab-content">
            <div class="section">
                <h2>📅 Bid Calendar</h2>
                <div class="calendar-nav">
                    <button onclick="changeMonth(-1)">← Previous</button>
                    <span class="calendar-month" id="calendarMonth"></span>
                    <button onclick="changeMonth(1)">Next →</button>
                </div>
                <div class="calendar">
                    <div class="calendar-header">Sun</div>
                    <div class="calendar-header">Mon</div>
                    <div class="calendar-header">Tue</div>
                    <div class="calendar-header">Wed</div>
                    <div class="calendar-header">Thu</div>
                    <div class="calendar-header">Fri</div>
                    <div class="calendar-header">Sat</div>
                </div>
                <div class="calendar" id="calendarGrid"></div>
                <div id="dayTenders" style="margin-top: 20px;"></div>
            </div>
        </div>
        
        <!-- SOURCES TAB -->
        <div id="sources" class="tab-content">
            <div class="section">
                <h2>🏢 Company Focus Areas</h2>
                <div class="companies">
                    <div class="company-card" style="border-color: rgba(72,219,251,0.5);">
                        <div class="company-name" style="color: #48dbfb;">💧 TES</div>
                        <div class="company-focus">Water Treatment & Cooling Specialists</div>
                        <div class="company-keywords">
                            <span class="keyword">Water Treatment</span>
                            <span class="keyword">Cooling Systems</span>
                            <span class="keyword">Chemical Dosing</span>
                            <span class="keyword">RO Systems</span>
                            <span class="keyword">Boiler Treatment</span>
                        </div>
                    </div>
                    <div class="company-card" style="border-color: rgba(254,202,87,0.5);">
                        <div class="company-name" style="color: #feca57;">⚙️ Phakathi</div>
                        <div class="company-focus">Mechanical & Electrical Solutions</div>
                        <div class="company-keywords">
                            <span class="keyword">Pumps</span>
                            <span class="keyword">Mechanical</span>
                            <span class="keyword">Fabrication</span>
                            <span class="keyword">Switchgear</span>
                            <span class="keyword">Valves</span>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="section">
                <h2>📊 Data Sources (11 Active)</h2>
                <div class="companies">
                    <div class="company-card" style="border-color: rgba(72,219,251,0.3);">
                        <div class="company-name" style="color: #48dbfb;">🏛️ Municipalities</div>
                        <div class="company-keywords">
                            <span class="keyword">Ekurhuleni</span>
                            <span class="keyword">Tshwane</span>
                            <span class="keyword">Cape Town</span>
                            <span class="keyword">eThekwini</span>
                        </div>
                    </div>
                    <div class="company-card" style="border-color: rgba(254,202,87,0.3);">
                        <div class="company-name" style="color: #feca57;">⚡ SOEs & Utilities</div>
                        <div class="company-keywords">
                            <span class="keyword">Eskom</span>
                            <span class="keyword">Transnet</span>
                            <span class="keyword">Rand Water</span>
                            <span class="keyword">Sasol</span>
                            <span class="keyword">SANEDI</span>
                            <span class="keyword">Johannesburg Water</span>
                            <span class="keyword">Umgeni Water</span>
                        </div>
                    </div>
                    <div class="company-card" style="border-color: rgba(255,107,107,0.3);">
                        <div class="company-name" style="color: #ff6b6b;">⛏️ Mining</div>
                        <div class="company-keywords">
                            <span class="keyword">Anglo American</span>
                            <span class="keyword">Harmony Gold</span>
                            <span class="keyword">Seriti</span>
                            <span class="keyword">Exxaro</span>
                        </div>
                    </div>
                    <div class="company-card" style="border-color: rgba(162,155,254,0.3);">
                        <div class="company-name" style="color: #a29bfe;">🏦 National Treasury</div>
                        <div class="company-keywords">
                            <span class="keyword">eTenders Portal</span>
                            <span class="keyword">Government Bids</span>
                        </div>
                    </div>
                </div>
            </div>
        </div>
        
        <footer>
            <p>Tender Intelligence System v3.0 | TES & Phakathi</p>
            <p>Automated scans: Daily 6AM | Weekly Reports: Monday 7AM</p>
        </footer>
    </div>
    
    <script>
        const tenders = {tenders_json};
        let currentFilter = 'all';
        let currentMonth = new Date();
        
        // Calculate days until closing
        function getDaysUntil(dateStr) {{
            if (!dateStr) return null;
            const closing = new Date(dateStr);
            const today = new Date();
            today.setHours(0,0,0,0);
            closing.setHours(0,0,0,0);
            return Math.ceil((closing - today) / (1000 * 60 * 60 * 24));
        }}
        
        function getCountdownHtml(dateStr) {{
            const days = getDaysUntil(dateStr);
            if (days === null) return '<span class="countdown normal">📅 TBC</span>';
            if (days < 0) return '<span class="countdown closed">CLOSED</span>';
            if (days === 0) return '<span class="countdown urgent">🔴 TODAY!</span>';
            if (days === 1) return '<span class="countdown urgent">🔴 TOMORROW!</span>';
            if (days <= 3) return `<span class="countdown urgent">⚠️ ${{days}} days</span>`;
            if (days <= 7) return `<span class="countdown warning">📅 ${{days}} days</span>`;
            return `<span class="countdown normal">📅 ${{days}} days</span>`;
        }}
        
        function renderTenders(filter) {{
            const list = document.getElementById('tenderList');
            let filtered = tenders.filter(t => getDaysUntil(t.closing_date) === null || getDaysUntil(t.closing_date) >= 0);
            
            if (filter === 'TES' || filter === 'Phakathi' || filter === 'Both') {{
                filtered = filtered.filter(t => t.company === filter);
            }} else if (filter === 'HIGH') {{
                filtered = filtered.filter(t => t.priority === 'HIGH');
            }} else if (filter === 'MEDIUM') {{
                filtered = filtered.filter(t => t.priority === 'MEDIUM');
            }} else if (filter === 'LOW') {{
                filtered = filtered.filter(t => t.priority === 'LOW');
            }}
            
            // Sort by closing date (urgent first)
            filtered.sort((a, b) => {{
                const daysA = getDaysUntil(a.closing_date) ?? 999;
                const daysB = getDaysUntil(b.closing_date) ?? 999;
                return daysA - daysB;
            }});
            
            if (filtered.length === 0) {{
                list.innerHTML = '<li class="empty-state"><h3>No tenders found</h3><p>Try a different filter...</p></li>';
                return;
            }}
            
            list.innerHTML = filtered.map(t => {{
                const desc = t.description && t.description !== t.title ? t.description : '';
                const isPdf = t.url && t.url.endsWith('.pdf');
                const daysLeft = getDaysUntil(t.closing_date);
                const urgencyClass = daysLeft !== null && daysLeft <= 3 ? 'urgent' : (daysLeft !== null && daysLeft <= 7 ? 'warning' : '');
                
                return `<li class="tender-item ${{urgencyClass}}" onclick="window.open('${{t.url}}', '_blank')">
                    <div class="tender-content">
                        <div class="tender-info">
                            <div class="tender-header">
                                <span class="tender-ref">${{t.ref}}</span>
                                <span class="company-badge company-${{t.company}}">${{t.company}}</span>
                                ${{getCountdownHtml(t.closing_date)}}
                            </div>
                            <div class="tender-title">${{t.title}} ${{isPdf ? '📄' : ''}}</div>
                            ${{desc ? `<div class="tender-description">${{desc}}</div>` : ''}}
                            <div class="tender-meta">
                                <span>📍 ${{t.client}}</span>
                                <span>📁 ${{t.category}}</span>
                                <span>🔗 ${{t.source}}</span>
                                ${{t.contact ? `<span>📞 ${{t.contact}}</span>` : ''}}
                                ${{t.pdf_size ? `<span>💾 ${{t.pdf_size}}</span>` : ''}}
                            </div>
                        </div>
                        <div class="tender-right">
                            <span class="priority-badge priority-${{t.priority}}">${{t.priority}}</span>
                            <div class="score">${{t.score}}</div>
                            <a href="${{t.url}}" target="_blank" rel="noopener" class="view-btn" onclick="event.stopPropagation()">
                                View ↗
                            </a>
                        </div>
                    </div>
                </li>`;
            }}).join('');
        }}
        
        function filterTenders(filter) {{
            currentFilter = filter;
            document.querySelectorAll('.filter-tab').forEach(tab => {{
                tab.classList.remove('active');
                if (tab.textContent.toLowerCase().includes(filter.toLowerCase()) || 
                    (filter === 'all' && tab.textContent.includes('All')) ||
                    (filter === 'HIGH' && tab.textContent.includes('Urgent'))) {{
                    tab.classList.add('active');
                }}
            }});
            renderTenders(filter);
        }}
        
        function showTab(tabId) {{
            document.querySelectorAll('.tab-content').forEach(t => t.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
            document.getElementById(tabId).classList.add('active');
            event.target.classList.add('active');
            
            if (tabId === 'calendar') renderCalendar();
        }}
        
        function renderCalendar() {{
            const grid = document.getElementById('calendarGrid');
            const monthLabel = document.getElementById('calendarMonth');
            
            const year = currentMonth.getFullYear();
            const month = currentMonth.getMonth();
            
            monthLabel.textContent = currentMonth.toLocaleDateString('en-ZA', {{ month: 'long', year: 'numeric' }});
            
            const firstDay = new Date(year, month, 1);
            const lastDay = new Date(year, month + 1, 0);
            const startDay = firstDay.getDay();
            const daysInMonth = lastDay.getDate();
            
            // Get tenders by date
            const tendersByDate = {{}};
            tenders.forEach(t => {{
                if (t.closing_date) {{
                    const date = t.closing_date;
                    if (!tendersByDate[date]) tendersByDate[date] = [];
                    tendersByDate[date].push(t);
                }}
            }});
            
            let html = '';
            const today = new Date();
            today.setHours(0,0,0,0);
            
            // Previous month days
            for (let i = 0; i < startDay; i++) {{
                const day = new Date(year, month, -(startDay - i - 1));
                html += `<div class="calendar-day other-month">${{day.getDate()}}</div>`;
            }}
            
            // Current month days
            for (let day = 1; day <= daysInMonth; day++) {{
                const date = new Date(year, month, day);
                const dateStr = date.toISOString().split('T')[0];
                const isToday = date.getTime() === today.getTime();
                const tendersOnDay = tendersByDate[dateStr] || [];
                const hasTenders = tendersOnDay.length > 0;
                
                html += `<div class="calendar-day ${{isToday ? 'today' : ''}} ${{hasTenders ? 'has-tenders' : ''}}" 
                    onclick="showDayTenders('${{dateStr}}')" title="${{tendersOnDay.length}} tender(s)">
                    ${{day}}
                    ${{hasTenders ? `<span class="tender-count">${{tendersOnDay.length}}</span>` : ''}}
                </div>`;
            }}
            
            grid.innerHTML = html;
        }}
        
        function showDayTenders(dateStr) {{
            const container = document.getElementById('dayTenders');
            const dayTenders = tenders.filter(t => t.closing_date === dateStr);
            
            if (dayTenders.length === 0) {{
                container.innerHTML = `<p style="color: #888; text-align: center;">No tenders closing on ${{dateStr}}</p>`;
                return;
            }}
            
            container.innerHTML = `
                <h3 style="margin-bottom: 15px;">📅 Closing on ${{new Date(dateStr).toLocaleDateString('en-ZA', {{ weekday: 'long', day: 'numeric', month: 'long' }})}}</h3>
                ${{dayTenders.map(t => `
                    <div style="background: rgba(255,255,255,0.05); padding: 15px; border-radius: 10px; margin: 10px 0; cursor: pointer;" onclick="window.open('${{t.url}}', '_blank')">
                        <span style="color: #667eea; font-weight: bold;">${{t.ref}}</span>
                        <span class="company-badge company-${{t.company}}" style="margin-left: 10px;">${{t.company}}</span>
                        <div style="color: #ccc; margin-top: 5px;">${{t.title}}</div>
                        <div style="color: #888; font-size: 0.8rem; margin-top: 5px;">📍 ${{t.client}}</div>
                    </div>
                `).join('')}}
            `;
        }}
        
        function changeMonth(delta) {{
            currentMonth.setMonth(currentMonth.getMonth() + delta);
            renderCalendar();
        }}
        
        // Initial render
        renderTenders('all');
    </script>
</body>
</html>'''
    return html

def push_to_github():
    """Push to GitHub (triggers Vercel auto-deploy)"""
    try:
        os.chdir(VERCEL_DIR)
        subprocess.run(["git", "add", "-A"], capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Sync: {datetime.now().strftime('%Y-%m-%d %H:%M')}"], capture_output=True)
        result = subprocess.run(["git", "push"], capture_output=True, text=True, timeout=60)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)

def sync():
    """Main sync function"""
    print("🔄 Syncing tender data to Vercel...")
    
    tenders = load_tenders()
    print(f"   Found {len(tenders)} tenders")
    
    html = generate_dashboard_html(tenders)
    
    os.makedirs(VERCEL_DIR, exist_ok=True)
    with open(DASHBOARD_HTML, "w") as f:
        f.write(html)
    print(f"   ✅ Dashboard HTML updated")
    
    print("   🚀 Pushing to GitHub (triggers Vercel auto-deploy)...")
    success, output = push_to_github()
    
    if success:
        print(f"   ✅ Pushed! Vercel will auto-deploy in ~30 seconds")
        print(f"   🌐 https://vercel-dashboard-roan.vercel.app")
        return True
    else:
        print(f"   ⚠️ Git push issue: {output[:100]}")
        return False

if __name__ == "__main__":
    sync()
