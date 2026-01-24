import openpyxl
from datetime import datetime
import os

EXCEL_PATH = "/Users/lazolasonqishe/Documents/MASTER/TENDERS/01_Tender_Log/Tender_Dashboard_v2.xlsx"
SHEET_NAME = "Tender_Log"

def test_read_excel():
    wb = openpyxl.load_workbook(EXCEL_PATH, data_only=True)
    sheet = wb[SHEET_NAME]
    headers = [cell.value for cell in sheet[1] if cell.value]
    print(f"Headers: {headers}")
    
    today = datetime.now().date()
    tenders = []
    
    for row in sheet.iter_rows(min_row=2, max_row=10, values_only=True):
        if not any(row): continue
        data = dict(zip(headers, row))
        print(f"Row data: {data}")
        
        # Mapping to internal format
        # Excel: 'Tender Name' -> Internal: 'title'
        # Excel: 'Closing Date' -> Internal: 'closing_date'
        
        closing = data.get('Closing Date')
        if isinstance(closing, datetime):
            val = closing.date()
            if val >= today:
                tenders.append(data)
    
    print(f"Active found in sample: {len(tenders)}")

if __name__ == "__main__":
    test_read_excel()
