# ==========================================================
# NATIONAL TREASURY eTenders SCRAPER
# Phase 1: API-based scraper for SA eTenders website
# ==========================================================

import requests
from datetime import datetime
import traceback
import json

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.text_cleaner import clean_text
from classify_engine import classify_tender


class NationalTreasuryScraper:

    def __init__(self, url: str, user_agent: str, timeout: int):
        # The API endpoint for fetching tenders
        self.api_url = "https://www.etenders.gov.za/Home/TenderOpportunities"
        self.headers = {
            "User-Agent": user_agent,
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "X-Requested-With": "XMLHttpRequest",
            "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8"
        }
        self.timeout = timeout

    # ------------------------------------------------------
    # FETCH TENDERS VIA API
    # ------------------------------------------------------
    def fetch_page(self):
        try:
            # POST request to get tender data
            # Parameters for "Currently Advertised" tenders
            payload = {
                "draw": 1,
                "start": 0,
                "length": 100,  # Get up to 100 tenders
                "tenderStatus": 1,  # 1 = Currently Advertised
                "categories": "",
                "provinces": "",
                "departments": ""
            }
            
            response = requests.post(
                self.api_url, 
                headers=self.headers, 
                data=payload,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response.json()
        except Exception as e:
            raise Exception(f"Error fetching National Treasury API → {e}")

    # ------------------------------------------------------
    # PARSE AND EXTRACT TENDER FIELDS FROM JSON
    # ------------------------------------------------------
    def parse_tenders(self, data):
        tenders = []
        
        # Handle different response formats
        if isinstance(data, dict) and "data" in data:
            items = data["data"]
        elif isinstance(data, list):
            items = data
        else:
            print(f"Unexpected data format: {type(data)}")
            return tenders

        for item in items:
            try:
                # Extract fields from JSON response
                # Adjust field names based on actual API response
                ref = clean_text(str(item.get("tenderNumber", item.get("TenderNumber", item.get("referenceNumber", "NA")))))
                title = clean_text(str(item.get("description", item.get("Description", item.get("title", "")))))
                client = clean_text(str(item.get("department", item.get("Department", item.get("organOfState", "Unknown")))))
                
                # Handle closing date
                closing_raw = item.get("closingDate", item.get("ClosingDate", ""))
                if closing_raw:
                    try:
                        # Try to parse various date formats
                        if "T" in str(closing_raw):
                            closing_date = str(closing_raw).split("T")[0]
                        else:
                            closing_date = str(closing_raw)[:10]
                    except:
                        closing_date = str(closing_raw)
                else:
                    closing_date = "TBD"
                
                description = clean_text(str(item.get("briefDescription", item.get("description", title))))
                
                # Skip if no title
                if not title or title == "None":
                    continue

                # Classification engine call
                classification = classify_tender(title, description)
                category = classification["category"]
                reason = classification["reason"]
                short_title = classification["short_title"]

                tenders.append({
                    "ref": ref if ref and ref != "NA" else "NT-" + str(len(tenders)),
                    "title": title,
                    "short_title": short_title,
                    "client": client,
                    "closing_date": closing_date,
                    "description": description,
                    "category": category,
                    "reason": reason
                })

            except Exception as e:
                traceback.print_exc()
                continue

        return tenders

    # ------------------------------------------------------
    # MAIN RUN METHOD
    # ------------------------------------------------------
    def run(self):
        data = self.fetch_page()
        tenders = self.parse_tenders(data)
        return tenders
