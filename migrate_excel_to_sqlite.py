import os
import sqlite3
import pandas as pd
from datetime import datetime
import re
import shutil

# Configuration
EXCEL_PATH = "01_Tender_Log/Tender_Dashboard_v2.xlsx"
DB_PATH = "data/tenders.db"

def clean_text(text):
    if pd.isna(text):
        return ""
    return str(text).strip()

def parse_excel_to_sqlite():
    if not os.path.exists(EXCEL_PATH):
        print(f"Error: Excel file not found at {EXCEL_PATH}")
        return

    # Create backup of Excel
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_path = EXCEL_PATH.replace(".xlsx", f"_backup_{timestamp}.xlsx")
    shutil.copy2(EXCEL_PATH, backup_path)
    print(f"Backup created at: {backup_path}")

    # Read Excel
    try:
        df = pd.read_excel(EXCEL_PATH, engine="openpyxl")
    except Exception as e:
        print(f"Error reading Excel: {e}")
        return

    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    count = 0
    duplicates = 0
    errors = 0

    for index, row in df.iterrows():
        try:
            # Column mapping (0-indexed)
            # 0: Tender Name, 1: Client, 2: Type, 3: Industry, 4: Fit Score, 
            # 5: Composite Score, 6: Priority, 7: Mexel Fit, 8: Stage, 
            # 9: Closing Date, 10: Status, 11: Next Action, 12: Notes, 
            # 13: Reference Number, 14: Date Added

            tender_name = clean_text(row.get("Tender Name", ""))
            client = clean_text(row.get("Client", ""))
            category = clean_text(row.get("Type", ""))
            industry_val = clean_text(row.get("Industry", ""))
            fit_score = row.get("Fit Score", 0)
            composite_score = row.get("Composite Score", 0)
            priority = clean_text(row.get("Priority", "MEDIUM"))
            mexel_suitability = row.get("Mexel Fit", 0)
            stage = clean_text(row.get("Stage", "New"))
            closing_date = clean_text(row.get("Closing Date", ""))
            status = clean_text(row.get("Status", "Open"))
            next_action = clean_text(row.get("Next Action", ""))
            notes = clean_text(row.get("Notes", ""))
            ref = clean_text(row.get("Reference Number", ""))
            date_added = clean_text(row.get("Date Added", ""))

            # Re-extract ref/title from tender_name if ref is missing
            if not ref or ref == "NA":
                match = re.search(r'^([A-Z0-9\-/]+)\s*-\s*(.*)', tender_name)
                if match:
                    ref = match.group(1).strip()
                    title = match.group(2).strip()
                else:
                    title = tender_name
            else:
                # If ref exists in its own column, tender_name might still contain it
                # Logic from excel_writer.py
                parts = str(tender_name).split(" - ", 1)
                if len(parts) == 2 and len(parts[0]) <= 60:
                    title = parts[1].strip()
                else:
                    title = tender_name

            # Parse Industry/Source
            # Format: "{source} ({industry_matched})"
            source = "Unknown"
            industry_scored = ""
            if industry_val:
                match = re.match(r"^(.*?)\s*\((.*?)\)", industry_val)
                if match:
                    source = match.group(1).strip()
                    industry_scored = match.group(2).strip()
                else:
                    source = industry_val

            # Normalize scores
            try: fit_score = float(fit_score)
            except: fit_score = 0.0
            try: composite_score = float(composite_score)
            except: composite_score = 0.0
            try: mexel_suitability = float(mexel_suitability)
            except: mexel_suitability = 0.0

            # Normalize date_added to created_at
            created_at = datetime.now().isoformat()
            if date_added:
                try:
                    # openpyxl might return datetime objects or strings
                    if isinstance(date_added, datetime):
                        created_at = date_added.isoformat()
                    else:
                        created_at = pd.to_datetime(date_added).isoformat()
                except:
                    pass

            # Insert into tenders table
            try:
                cursor.execute("""
                    INSERT INTO tenders (
                        ref, title, description, client, source, 
                        closing_date, category, classification_reason,
                        fit_score, industry_score, mexel_suitability, 
                        composite_score, priority, stage, status, 
                        next_action, notes, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    ref or f"MIG-{index}", # Ensure unique ref for migration
                    title,
                    "", # Description not separated in Excel
                    client,
                    source,
                    closing_date,
                    category,
                    notes.split("\n")[0] if "\n" in notes else "", # Heuristic for reason
                    fit_score,
                    0.0, # industry_score not directly in Excel (Industry Matched is a string)
                    mexel_suitability,
                    composite_score,
                    priority,
                    stage,
                    status,
                    next_action,
                    notes,
                    created_at
                ))
                count += 1
            except sqlite3.IntegrityError:
                duplicates += 1
                # print(f"Skipped duplicate ref: {ref}")

        except Exception as e:
            print(f"Error processing row {index}: {e}")
            errors += 1

    conn.commit()
    conn.close()

    print("\nMigration Summary:")
    print(f"Rows Migrated: {count}")
    print(f"Duplicates Skipped: {duplicates}")
    print(f"Errors Encountered: {errors}")

if __name__ == "__main__":
    parse_excel_to_sqlite()
