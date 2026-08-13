-- Schema migrations (ordered, additive changes)
CREATE TABLE IF NOT EXISTS schema_migrations (
    version INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    applied_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tenders table (main data)
CREATE TABLE IF NOT EXISTS tenders (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    ref TEXT UNIQUE NOT NULL,
    title TEXT NOT NULL,
    description TEXT,
    client TEXT,
    source TEXT,
    url TEXT,
    closing_date TEXT,
    
    -- Classification
    category TEXT,  -- MEXEL, EXCLUDED, etc.
    classification_reason TEXT,
    
    -- Scoring
    fit_score REAL,
    industry_score REAL,
    mexel_suitability REAL,
    composite_score REAL,
    priority TEXT,  -- HIGH, MEDIUM, LOW
    recommendation TEXT,
    
    -- Metadata
    stage TEXT DEFAULT 'New',
    status TEXT DEFAULT 'Open',
    next_action TEXT,
    notes TEXT,
    matched_keywords TEXT, -- Store keywords directly for faster access
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Bid Outcomes Table
CREATE TABLE IF NOT EXISTS bid_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT NOT NULL,
    company TEXT NOT NULL,
    bid_submitted BOOLEAN DEFAULT 0,
    bid_amount REAL,
    outcome TEXT NOT NULL, -- won, lost, withdrawn, no_bid
    winner_name TEXT,
    winning_amount REAL,
    bid_date TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_ref, company)
);

-- Bid Notes Table
CREATE TABLE IF NOT EXISTS bid_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT NOT NULL,
    company TEXT NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- PDF Analysis Table
CREATE TABLE IF NOT EXISTS pdf_analysis (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref TEXT UNIQUE NOT NULL,
    page_count INTEGER,
    word_count INTEGER,
    requirements TEXT, -- JSON array
    deadlines TEXT,    -- JSON array
    values_extracted TEXT, -- JSON array
    contact_info TEXT, -- JSON object
    full_text TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Planned procurement opportunities (early-warning pipeline)
CREATE TABLE IF NOT EXISTS planned_opportunities (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT UNIQUE NOT NULL,
    institution TEXT NOT NULL,
    description TEXT NOT NULL,
    planned_advert_date TEXT,
    planned_closing_date TEXT,
    planned_award_date TEXT,
    category TEXT,
    classification_reason TEXT,
    matched_keywords TEXT,
    lifecycle_stage TEXT NOT NULL DEFAULT 'PLANNED',
    source TEXT NOT NULL,
    source_url TEXT,
    matched_tender_ref TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    retired_at TIMESTAMP,
    first_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    last_seen_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (matched_tender_ref) REFERENCES tenders(ref)
);

-- Auditable links from early-warning plans to advertised tenders
CREATE TABLE IF NOT EXISTS planned_opportunity_matches (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    external_id TEXT NOT NULL UNIQUE,
    tender_ref TEXT NOT NULL,
    match_score REAL NOT NULL,
    match_method TEXT NOT NULL,
    evidence TEXT NOT NULL,
    matched_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (external_id) REFERENCES planned_opportunities(external_id),
    FOREIGN KEY (tender_ref) REFERENCES tenders(ref)
);

-- Classifications table (audit trail)
CREATE TABLE IF NOT EXISTS classifications (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_id INTEGER,
    matched_keywords TEXT,
    classification_reason TEXT,
    classified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_id) REFERENCES tenders(id)
);

-- Authorized private-feed import audit (no feed content or credentials stored)
CREATE TABLE IF NOT EXISTS authorized_feed_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source_id TEXT NOT NULL,
    file_name TEXT NOT NULL,
    file_sha256 TEXT NOT NULL,
    dry_run INTEGER NOT NULL DEFAULT 0,
    status TEXT NOT NULL,
    records_total INTEGER NOT NULL DEFAULT 0,
    records_valid INTEGER NOT NULL DEFAULT 0,
    records_invalid INTEGER NOT NULL DEFAULT 0,
    records_excluded INTEGER NOT NULL DEFAULT 0,
    records_inserted INTEGER NOT NULL DEFAULT 0,
    records_updated INTEGER NOT NULL DEFAULT 0,
    records_unchanged INTEGER NOT NULL DEFAULT 0,
    error_type TEXT,
    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    finished_at TIMESTAMP,
    UNIQUE(source_id, file_sha256, dry_run)
);

-- Scraper runs table (monitoring)
CREATE TABLE IF NOT EXISTS scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    started_at TEXT,
    finished_at TEXT,
    duration_seconds REAL,
    tenders_found INTEGER,
    tenders_new INTEGER,
    status TEXT,
    error_message TEXT
);

-- Indexes for performance
CREATE INDEX IF NOT EXISTS idx_tenders_ref ON tenders(ref);
CREATE INDEX IF NOT EXISTS idx_tenders_priority ON tenders(priority);
CREATE INDEX IF NOT EXISTS idx_tenders_category ON tenders(category);
CREATE INDEX IF NOT EXISTS idx_tenders_closing_date ON tenders(closing_date);
CREATE INDEX IF NOT EXISTS idx_tenders_created_at ON tenders(created_at);
CREATE INDEX IF NOT EXISTS idx_scraper_runs_source_run_date ON scraper_runs(source, run_date DESC);
CREATE INDEX IF NOT EXISTS idx_planned_opportunities_advert_date ON planned_opportunities(planned_advert_date);
CREATE INDEX IF NOT EXISTS idx_planned_opportunities_category_stage ON planned_opportunities(category, lifecycle_stage);
CREATE INDEX IF NOT EXISTS idx_planned_matches_tender_ref ON planned_opportunity_matches(tender_ref);
CREATE INDEX IF NOT EXISTS idx_authorized_feed_runs_source_started
    ON authorized_feed_runs(source_id, started_at DESC);
