# ==========================================================
# EXCEL WRITER UTILITY
# Writes tender data to Excel with AI scoring columns
# ==========================================================

import os
import sys
from openpyxl import Workbook, load_workbook
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from datetime import datetime

# Assuming these are in the parent directory, adjust if necessary
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from classify_engine import classify_tender
from scoring_engine import score_tender


# Column headers (with new scoring columns)
HEADERS = [
    "Tender Name",
    "Client",
    "Type",
    "Industry",
    "Fit Score",
    "Composite Score",
    "Priority",
    "TES Fit",
    "Phakathi Fit",
    "Risk Level",
    "Revenue Potential",
    "Stage",
    "Closing Date",
    "Status",
    "Next Action",
    "Notes",
    "Reference Number",
    "Date Added"
]

# Priority colors
PRIORITY_COLORS = {
    "HIGH": "FF6B6B",     # Red
    "MEDIUM": "FFE66D",   # Yellow
    "LOW": "C8E6C9"       # Green
}


class ExcelWriter:
    """Writes tender data to Excel spreadsheet with scoring"""
    
    def __init__(self, file_path: str, sheet_name: str = "Tender_Log"):
        self.file_path = file_path
        self.sheet_name = sheet_name
        self._ensure_workbook()
    
    def _ensure_workbook(self):
        """Create workbook if it doesn't exist"""
        if os.path.exists(self.file_path):
            self.wb = load_workbook(self.file_path)
        else:
            self.wb = Workbook()
            self.wb.active.title = self.sheet_name
            self._write_headers()
            self.wb.save(self.file_path)
    
    def _write_headers(self):
        """Write column headers with formatting"""
        ws = self.wb.active
        
        # Header style
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill(start_color="2E7D32", end_color="2E7D32", fill_type="solid")
        
        for col, header in enumerate(HEADERS, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")
        
        # Set column widths
        col_widths = {
            'A': 40,  # Tender Name
            'B': 20,  # Client
            'C': 12,  # Type
            'D': 25,  # Industry
            'E': 10,  # Fit Score
            'F': 14,  # Composite Score
            'G': 10,  # Priority
            'H': 10,  # TES Fit
            'I': 12,  # Phakathi Fit
            'J': 12,  # Risk Level
            'K': 15,  # Revenue Potential
            'L': 10,  # Stage
            'M': 12,  # Closing Date
            'N': 10,  # Status
            'O': 15,  # Next Action
            'P': 50,  # Notes
            'Q': 20,  # Reference Number
            'R': 12,  # Date Added
        }
        
        for col_letter, width in col_widths.items():
            ws.column_dimensions[col_letter].width = width
    
    def _get_existing_references(self):
        """Get set of existing tender reference numbers"""
        ws = self.wb.active
        existing = set()
        
        for row in range(2, ws.max_row + 1):
            ref = ws.cell(row=row, column=17).value  # Reference Number column
            if ref:
                existing.add(str(ref).strip().upper())
        
        return existing
    
    def write_tender(self, tender_name: str, client: str, tender_type: str,
                    industry: str, fit_score: int, stage: str, closing_date: str,
                    status: str, next_action: str, notes: str, reference_number: str,
                    composite_score: float = None, priority: str = None,
                    risk_level: str = None, revenue_potential: str = None,
                    tes_fit: int = None, phakathi_fit: int = None) -> bool:
        """
        Write a single tender to Excel
        Returns True if added, False if duplicate
        """
        
        # Check for duplicates
        existing = self._get_existing_references()
        ref_normalized = str(reference_number).strip().upper()
        
        if ref_normalized and ref_normalized != "NA" and ref_normalized in existing:
            return False  # Duplicate
        
        # Also check by tender name
        ws = self.wb.active
        for row in range(2, ws.max_row + 1):
            existing_name = ws.cell(row=row, column=1).value
            if existing_name and existing_name.strip().upper() == tender_name.strip().upper():
                return False  # Duplicate
        
        # Add new row
        row = ws.max_row + 1
        
        data = [
            tender_name,
            client,
            tender_type,
            industry,
            fit_score,
            composite_score or fit_score,
            priority or "MEDIUM",
            tes_fit or 0,
            phakathi_fit or 0,
            risk_level or "Medium",
            revenue_potential or "Medium",
            stage,
            closing_date,
            status,
            next_action,
            notes,
            reference_number,
            datetime.now().strftime("%Y-%m-%d")
        ]
        
        for col, value in enumerate(data, 1):
            cell = ws.cell(row=row, column=col, value=value)
            
            # Apply priority color to the row
            if priority and priority in PRIORITY_COLORS:
                cell.fill = PatternFill(
                    start_color=PRIORITY_COLORS[priority],
                    end_color=PRIORITY_COLORS[priority],
                    fill_type="solid"
                )
        
        # Save workbook
        self.wb.save(self.file_path)
        return True

    def add_tender_with_scoring(self, tender_data: dict):
        """
        Scores a tender and writes it to the Excel file.
        """
        # Classify tender (returns dict)
        classification = classify_tender(tender_data["title"], tender_data["description"])
        category = classification["category"]
        reason = classification["reason"]
        short_title = classification["short_title"]

        tender_name = f"{tender_data['ref']} - {tender_data['title']}" if tender_data['ref'] and tender_data['ref'] != "NA" else tender_data['title']

        # AI SCORING ENGINE
        scores = score_tender(
            title=tender_data["title"],
            description=tender_data["description"],
            client=tender_data["client"],
            closing_date=tender_data["closing_date"],
            category=category
        )

        fit_score = scores["fit_score"]
        composite_score = scores["composite_score"]
        priority = scores["priority"]
        recommendation = scores["recommendation"]

        # Build notes with scoring info
        enhanced_notes = f"{reason}\n" if reason else ""
        enhanced_notes += f"[AI Score: {composite_score}/10 | Priority: {priority}]"
        enhanced_notes += f"\n{recommendation}"

        # Write to Excel
        was_added = self.write_tender(
            tender_name=tender_name,
            client=tender_data["client"],
            tender_type=category,
            industry=f"{tender_data['source']} ({scores['industry_matched']})",
            fit_score=fit_score,
            stage="New",
            closing_date=tender_data["closing_date"],
            status="Open",
            next_action="Review" if priority == "LOW" else "Prepare Bid" if priority == "MEDIUM" else "URGENT BID",
            notes=enhanced_notes,
            reference_number=tender_data["ref"],
            composite_score=composite_score,
            priority=priority,
            risk_level=scores["risk_level"],
            revenue_potential=scores["revenue_potential"],
            tes_fit=scores["tes_suitability"],
            phakathi_fit=scores["phakathi_suitability"]
        )

        return was_added, scores, classification
    
    def get_stats(self):
        """Get tender statistics"""
        ws = self.wb.active
        
        stats = {
            "total": ws.max_row - 1,  # Exclude header
            "by_type": {},
            "by_priority": {"HIGH": 0, "MEDIUM": 0, "LOW": 0},
            "by_status": {}
        }
        
        for row in range(2, ws.max_row + 1):
            # By type
            t_type = ws.cell(row=row, column=3).value or "Unknown"
            stats["by_type"][t_type] = stats["by_type"].get(t_type, 0) + 1
            
            # By priority
            priority = ws.cell(row=row, column=7).value or "MEDIUM"
            if priority in stats["by_priority"]:
                stats["by_priority"][priority] += 1
            
            # By status
            status = ws.cell(row=row, column=14).value or "Unknown"
            stats["by_status"][status] = stats["by_status"].get(status, 0) + 1
        
        return stats


# ==========================================================
# STANDALONE TEST
# ==========================================================
if __name__ == "__main__":
    # Test
    writer = ExcelWriter("/tmp/test_tender_log.xlsx", "Tender_Log")
    
    added = writer.write_tender(
        tender_name="TEST-001 - Cooling Water Treatment",
        client="Eskom",
        tender_type="TES",
        industry="Power Generation",
        fit_score=8,
        stage="New",
        closing_date="2025-12-15",
        status="Open",
        next_action="Prepare Bid",
        notes="Test tender",
        reference_number="TEST-001",
        composite_score=8.5,
        priority="HIGH",
        risk_level="Low",
        revenue_potential="High",
        tes_fit=9,
        phakathi_fit=2
    )
    
    print(f"Added: {added}")
    print(f"Stats: {writer.get_stats()}")
