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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
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
