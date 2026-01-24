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
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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

-- Scraper runs table (monitoring)
CREATE TABLE IF NOT EXISTS scraper_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    source TEXT,
    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
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
