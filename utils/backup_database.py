#!/usr/bin/env python3
import os
import shutil
from datetime import datetime
import sqlite3

def backup_database():
    """Create a backup of the SQLite database."""
    PROJECT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    DB_PATH = os.path.join(PROJECT_DIR, "data", "tenders.db")
    BACKUP_DIR = os.path.join(PROJECT_DIR, "backups")
    
    if not os.path.exists(DB_PATH):
        print(f"Error: Database not found at {DB_PATH}")
        return False
        
    os.makedirs(BACKUP_DIR, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = os.path.join(BACKUP_DIR, f"tenders_backup_{timestamp}.db")
    
    try:
        # Use sqlite3 backup API if available, else copy file
        # Copying is generally safe if no one is writing, but backup API is better
        with sqlite3.connect(DB_PATH) as src:
            with sqlite3.connect(backup_path) as dst:
                src.backup(dst)
        
        print(f"✅ Database backup created: {backup_path}")
        
        # Cleanup old backups (keep last 30)
        backups = sorted([f for f in os.listdir(BACKUP_DIR) if f.startswith("tenders_backup_")])
        if len(backups) > 30:
            for b in backups[:-30]:
                os.remove(os.path.join(BACKUP_DIR, b))
            print(f"   Cleaned up {len(backups) - 30} old backups.")
            
        return True
    except Exception as e:
        print(f"❌ Backup failed: {e}")
        return False

if __name__ == "__main__":
    backup_database()
