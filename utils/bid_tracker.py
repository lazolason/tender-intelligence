# ==========================================================
# BID OUTCOME TRACKER - Track bid submissions and results
# ==========================================================

import logging
import sqlite3
from datetime import datetime, date
from typing import Dict, List, Optional, Tuple
from contextlib import contextmanager

logger = logging.getLogger(__name__)


# ==========================================================
# DATABASE SCHEMA
# ==========================================================

CREATE_TABLES_SQL = """
-- Bid Outcomes Table
CREATE TABLE IF NOT EXISTS bid_outcomes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref VARCHAR(50) NOT NULL,
    company VARCHAR(20) NOT NULL,
    bid_submitted BOOLEAN DEFAULT 0,
    bid_amount DECIMAL(12,2),
    outcome VARCHAR(20) NOT NULL,
    winner_name VARCHAR(100),
    winning_amount DECIMAL(12,2),
    bid_date DATE NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(tender_ref, company)
);

-- Bid Notes Table
CREATE TABLE IF NOT EXISTS bid_notes (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    tender_ref VARCHAR(50) NOT NULL,
    note TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (tender_ref) REFERENCES bid_outcomes(tender_ref) ON DELETE CASCADE
);

-- Indexes for common queries
CREATE INDEX IF NOT EXISTS idx_tender_ref ON bid_outcomes(tender_ref);
CREATE INDEX IF NOT EXISTS idx_company ON bid_outcomes(company);
CREATE INDEX IF NOT EXISTS idx_outcome ON bid_outcomes(outcome);
CREATE INDEX IF NOT EXISTS idx_bid_date ON bid_outcomes(bid_date);
"""


# ==========================================================
# DATABASE CONNECTION
# ==========================================================

@contextmanager
def get_db_connection(db_path: str):
    """
    Context manager for database connections
    
    Args:
        db_path: Path to SQLite database file
        
    Yields:
        Database connection object
    """
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn


def init_database(db_path: str) -> bool:
    """
    Initialize database with schema
    
    Args:
        db_path: Path to SQLite database file
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection(db_path) as conn:
            conn.executescript(CREATE_TABLES_SQL)
            conn.commit()
        logger.info(f"Database initialized at {db_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return False


# ==========================================================
# BID OUTCOME FUNCTIONS
# ==========================================================

def record_bid_outcome(
    db_path: str,
    tender_ref: str,
    company: str,
    bid_submitted: bool,
    outcome: str,
    bid_amount: Optional[float] = None,
    winner_name: Optional[str] = None,
    winning_amount: Optional[float] = None,
    bid_date: Optional[str] = None
) -> bool:
    """
    Record a bid outcome for a tender
    
    Args:
        db_path: Path to database file
        tender_ref: Tender reference number
        company: Company name (TES or Phakathi)
        bid_submitted: Whether bid was submitted
        bid_amount: Bid amount in ZAR
        outcome: Bid result (won, lost, withdrawn, no_bid)
        winner_name: Name of winning company
        winning_amount: Winning bid amount in ZAR
        bid_date: Date of bid submission (YYYY-MM-DD)
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection(db_path) as conn:
            # Check if record already exists
            cursor = conn.cursor()
            cursor.execute(
                "SELECT id FROM bid_outcomes WHERE tender_ref = ? AND company = ?",
                (tender_ref, company)
            )
            existing = cursor.fetchone()
            
            if existing:
                # Update existing record
                cursor.execute("""
                    UPDATE bid_outcomes
                    SET bid_submitted = ?, bid_amount = ?, outcome = ?,
                        winner_name = ?, winning_amount = ?, bid_date = ?
                    WHERE id = ?
                """, (bid_submitted, bid_amount, outcome, winner_name, winning_amount, bid_date, existing[0]))
                logger.info(f"Updated bid outcome for {tender_ref} ({company}): {outcome}")
            else:
                # Insert new record
                cursor.execute("""
                    INSERT INTO bid_outcomes 
                    (tender_ref, company, bid_submitted, bid_amount, outcome, winner_name, winning_amount, bid_date)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (tender_ref, company, bid_submitted, bid_amount, outcome, winner_name, winning_amount, bid_date))
                logger.info(f"Recorded bid outcome for {tender_ref} ({company}): {outcome}")
            
            conn.commit()
            return True
    except Exception as e:
        logger.error(f"Failed to record bid outcome: {e}")
        return False


def add_bid_note(db_path: str, tender_ref: str, company: str, note: str) -> bool:
    """
    Add a note to a tender's bid record
    
    Args:
        db_path: Path to database file
        tender_ref: Tender reference number
        company: Company name
        note: Note text
        
    Returns:
        True if successful, False otherwise
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO bid_notes (tender_ref, company, note)
                VALUES (?, ?, ?)
            """, (tender_ref, company, note))
            conn.commit()
            logger.info(f"Added note for {tender_ref} ({company})")
            return True
    except Exception as e:
        logger.error(f"Failed to add bid note: {e}")
        return False


def get_bid_outcome(db_path: str, tender_ref: str, company: str) -> Optional[Dict]:
    """
    Get bid outcome for a specific tender
    
    Args:
        db_path: Path to database file
        tender_ref: Tender reference number
        company: Company name
        
    Returns:
        Dictionary with bid outcome data, or None if not found
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bid_outcomes 
                WHERE tender_ref = ? AND company = ?
            """, (tender_ref, company))
            row = cursor.fetchone()
            
            if row:
                return {
                    'id': row[0],
                    'tender_ref': row[1],
                    'company': row[2],
                    'bid_submitted': bool(row[3]),
                    'bid_amount': float(row[4]) if row[4] else None,
                    'outcome': row[5],
                    'winner_name': row[6],
                    'winning_amount': float(row[7]) if row[7] else None,
                    'bid_date': row[8],
                    'created_at': row[9]
                }
            return None
    except Exception as e:
        logger.error(f"Failed to get bid outcome: {e}")
        return None


def get_bid_notes(db_path: str, tender_ref: str, company: str) -> List[Dict]:
    """
    Get all notes for a tender
    
    Args:
        db_path: Path to database file
        tender_ref: Tender reference number
        company: Company name
        
    Returns:
        List of note dictionaries
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM bid_notes 
                WHERE tender_ref = ? AND company = ?
                ORDER BY created_at DESC
            """, (tender_ref, company))
            rows = cursor.fetchall()
            
            return [
                {
                    'id': row[0],
                    'tender_ref': row[1],
                    'company': row[2],
                    'note': row[3],
                    'created_at': row[4]
                }
                for row in rows
            ]
    except Exception as e:
        logger.error(f"Failed to get bid notes: {e}")
        return []


# ==========================================================
# ANALYTICS FUNCTIONS
# ==========================================================

def get_win_rates(
    db_path: str,
    company: Optional[str] = None,
    period_start: Optional[str] = None,
    period_end: Optional[str] = None
) -> Dict:
    """
    Calculate win rates by various dimensions
    
    Args:
        db_path: Path to database file
        company: Filter by company (TES or Phakathi)
        period_start: Start date (YYYY-MM-DD)
        period_end: End date (YYYY-MM-DD)
        
    Returns:
        Dictionary with win rate statistics
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Build query with optional filters
            query = "SELECT * FROM bid_outcomes WHERE bid_submitted = 1"
            params = []
            
            if company:
                query += " AND company = ?"
                params.append(company)
            
            if period_start:
                query += " AND bid_date >= ?"
                params.append(period_start)
            
            if period_end:
                query += " AND bid_date <= ?"
                params.append(period_end)
            
            cursor.execute(query, params)
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    'total_bids': 0,
                    'wins': 0,
                    'losses': 0,
                    'withdrawals': 0,
                    'win_rate': 0.0,
                    'by_category': {},
                    'by_client': {},
                    'by_outcome': {}
                }
            
            # Calculate statistics
            total_bids = len(rows)
            wins = sum(1 for row in rows if row[5] == 'won')
            losses = sum(1 for row in rows if row[5] == 'lost')
            withdrawals = sum(1 for row in rows if row[5] == 'withdrawn')
            win_rate = wins / total_bids if total_bids > 0 else 0.0
            
            # By category
            by_category = {}
            for row in rows:
                # Get tender category from tender_ref (simplified)
                category = _infer_category_from_ref(row[1])
                if category not in by_category:
                    by_category[category] = {'bids': 0, 'wins': 0, 'win_rate': 0.0}
                by_category[category]['bids'] += 1
                if row[5] == 'won':
                    by_category[category]['wins'] += 1
            
            for cat in by_category:
                bids = by_category[cat]['bids']
                by_category[cat]['win_rate'] = by_category[cat]['wins'] / bids if bids > 0 else 0.0
            
            # By client
            by_client = {}
            for row in rows:
                client = _infer_client_from_ref(row[1])
                if client not in by_client:
                    by_client[client] = {'bids': 0, 'wins': 0, 'win_rate': 0.0}
                by_client[client]['bids'] += 1
                if row[5] == 'won':
                    by_client[client]['wins'] += 1
            
            for client in by_client:
                bids = by_client[client]['bids']
                by_client[client]['win_rate'] = by_client[client]['wins'] / bids if bids > 0 else 0.0
            
            # By outcome type
            by_outcome = {}
            for outcome in ['won', 'lost', 'withdrawn']:
                count = sum(1 for row in rows if row[5] == outcome)
                by_outcome[outcome] = count
            
            return {
                'total_bids': total_bids,
                'wins': wins,
                'losses': losses,
                'withdrawals': withdrawals,
                'win_rate': win_rate,
                'by_category': by_category,
                'by_client': by_client,
                'by_outcome': by_outcome,
                'period': {
                    'start': period_start,
                    'end': period_end
                }
            }
    except Exception as e:
        logger.error(f"Failed to calculate win rates: {e}")
        return {
            'total_bids': 0,
            'wins': 0,
            'losses': 0,
            'withdrawals': 0,
            'win_rate': 0.0,
            'by_category': {},
            'by_client': {},
            'by_outcome': {}
        }


def get_client_performance(db_path: str, client: str, limit: int = 20) -> Dict:
    """
    Get performance metrics for a specific client
    
    Args:
        db_path: Path to database file
        client: Client name to analyze
        limit: Maximum number of tenders to return
        
    Returns:
        Dictionary with client performance data
    """
    try:
        with get_db_connection(db_path) as conn:
            cursor = conn.cursor()
            
            # Get all bids for this client
            cursor.execute("""
                SELECT * FROM bid_outcomes
                WHERE company = ? AND bid_submitted = 1
                ORDER BY bid_date DESC
                LIMIT ?
            """, (client, limit))
            rows = cursor.fetchall()
            
            if not rows:
                return {
                    'client': client,
                    'total_bids': 0,
                    'wins': 0,
                    'win_rate': 0.0,
                    'recent_bids': []
                }
            
            total_bids = len(rows)
            wins = sum(1 for row in rows if row[5] == 'won')
            win_rate = wins / total_bids if total_bids > 0 else 0.0
            
            # Get recent bids
            recent_bids = [
                {
                    'tender_ref': row[1],
                    'outcome': row[5],
                    'bid_amount': float(row[4]) if row[4] else None,
                    'bid_date': row[8]
                }
                for row in rows[:10]
            ]
            
            return {
                'client': client,
                'total_bids': total_bids,
                'wins': wins,
                'win_rate': win_rate,
                'recent_bids': recent_bids
            }
    except Exception as e:
        logger.error(f"Failed to get client performance: {e}")
        return {
            'client': client,
            'total_bids': 0,
            'wins': 0,
            'win_rate': 0.0,
            'recent_bids': []
        }


def _infer_category_from_ref(ref: str) -> str:
    """
    Infer tender category from reference number
    
    Args:
        ref: Tender reference number
        
    Returns:
        Category (TES, Phakathi, Both, Unknown)
    """
    ref_upper = ref.upper()
    
    # National Treasury tenders
    if ref_upper.startswith('NT'):
        return 'TES'
    
    # Eskom tenders
    if ref_upper.startswith('ESK') or ref_upper.startswith('E'):
        return 'Phakathi'
    
    # Johannesburg Water tenders
    if ref_upper.startswith('JW') or ref_upper.startswith('RFQJW'):
        return 'Phakathi'
    
    # Default
    return 'Unknown'


def _infer_client_from_ref(ref: str) -> str:
    """
    Infer client from reference number
    
    Args:
        ref: Tender reference number
        
    Returns:
        Client name
    """
    ref_upper = ref.upper()
    
    # National Treasury
    if ref_upper.startswith('NT'):
        return 'National Treasury'
    
    # Eskom
    if ref_upper.startswith('ESK') or ref_upper.startswith('E'):
        return 'Eskom'
    
    # Johannesburg Water
    if ref_upper.startswith('JW') or ref_upper.startswith('RFQJW'):
        return 'Johannesburg Water'
    
    # Rand Water
    if 'RW' in ref_upper:
        return 'Rand Water'
    
    # Transnet
    if ref_upper.startswith('CPK'):
        return 'Transnet'
    
    # Default
    return 'Unknown'


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test with in-memory database
    import tempfile
    import os
    
    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_db:
        db_path = tmp.name
        
        # Initialize database
        if not init_database(db_path):
            print("Failed to initialize test database")
            exit(1)
        
        print("=" * 60)
        print("BID OUTCOME TRACKER TEST")
        print("=" * 60)
        
        # Test recording bid outcomes
        print("\n--- Recording Bid Outcomes ---")
        
        record_bid_outcome(db_path, "NT-001", "TES", True, 500000.0, "won", None, None, "2025-01-15")
        record_bid_outcome(db_path, "NT-002", "TES", True, 750000.0, "lost", "Competitor X", 600000.0, "2025-01-20")
        record_bid_outcome(db_path, "ESK-001", "Phakathi", True, 1200000.0, "won", None, None, "2025-01-10")
        record_bid_outcome(db_path, "ESK-002", "Phakathi", False, None, "withdrawn", None, None, "2025-01-05")
        
        # Test adding notes
        print("\n--- Adding Notes ---")
        add_bid_note(db_path, "NT-001", "TES", "Strong technical proposal, good pricing")
        add_bid_note(db_path, "ESK-001", "Phakathi", "Follow up on technical questions")
        
        # Test retrieving outcomes
        print("\n--- Retrieving Bid Outcomes ---")
        
        outcome = get_bid_outcome(db_path, "NT-001", "TES")
        if outcome:
            print(f"NT-001 (TES): {outcome['outcome']}, Bid: R{outcome['bid_amount']:,.0f}")
        
        notes = get_bid_notes(db_path, "NT-001", "TES")
        print(f"NT-001 (TES) Notes: {len(notes)} note(s)")
        
        # Test analytics
        print("\n--- Analytics ---")
        
        win_rates = get_win_rates(db_path)
        print(f"Overall Win Rate: {win_rates['win_rate']:.1%} ({win_rates['wins']}/{win_rates['total_bids']})")
        print(f"  By Category:")
        for cat, stats in win_rates['by_category'].items():
            print(f"  {cat}: {stats['win_rate']:.1%} ({stats['wins']}/{stats['bids']})")
        
        print(f"\nBy Client:")
        for client, stats in win_rates['by_client'].items():
            print(f"  {client}: {stats['win_rate']:.1%} ({stats['wins']}/{stats['bids']})")
        
        # Test client performance
        print("\n--- Client Performance ---")
        
        tes_perf = get_client_performance(db_path, "TES")
        print(f"TES Performance: {tes_perf['win_rate']:.1%} win rate ({tes_perf['wins']}/{tes_perf['total_bids']})")
        print(f"Recent TES bids:")
        for bid in tes_perf['recent_bids']:
            print(f"  {bid['tender_ref']}: {bid['outcome']} - R{bid['bid_amount']:,.0f if bid['bid_amount'] else 'N/A'}")
        
        # Cleanup
        os.unlink(db_path)
        print("\n--- Test Complete ---")
