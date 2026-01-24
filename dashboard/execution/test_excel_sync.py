import openpyxl
from datetime import datetime
import json
import os

EXCEL_PATH = "/Users/lazolasonqishe/Documents/MASTER/TENDERS/01_Tender_Log/Tender_Dashboard_v2.xlsx"
SHEET_NAME = "Tender_Log"

def test_read_excel():
    if not os.path.exists(EXCEL_PATH):
        print(f"Error: Excel file not found at {EXCEL_PATH}")
        return

    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    sheet = wb[SHEET_NAME]
    
    # Get headers
    headers = [cell.value for cell in sheet[1]]
    print(f"Headers found: {headers}")
    
    tenders = []
    today = datetime.now().date()
    
    # Iterate through rows (skip header)
    for row in sheet.iter_rows(min_row=2, values_only=True):
        if not any(row): continue
        
        tender = dict(zip(headers, row))
        
        # Filter for active tenders
        closing_date = tender.get('closing_date')
        if isinstance(closing_date, datetime):
            closing_date_val = closing_date.date()
        elif isinstance(closing_date, str):
            try:
                closing_date_val = datetime.strptime(closing_date, "%Y-%m-%d").date()
            except:
                closing_date_val = None
        else:
            closing_date_val = None
            
        if closing_date_val and closing_date_val >= today:
            tenders.append(tender)
            
    print(f"Found {len(tenders)} active tenders in Excel log.")
    if tenders:
        print(f"Sample: {tenders[0]['ref']} - {tenders[0]['title'][:50]}")

if __name__ == "__main__":
    test_read_excel()
