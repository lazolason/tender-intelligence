# ==========================================================
# FOLDER CREATION UTILITY
# Creates tender folders using your MASTER structure
# ==========================================================

import os
import re
from datetime import datetime

# ----------------------------------------------------------
# SANITISE FOLDER NAME (remove illegal characters)
# ----------------------------------------------------------
def clean_name(name: str) -> str:
    name = name.replace(" ", "_")
    name = re.sub(r"[^A-Za-z0-9_\-]", "", name)
    return name.strip("_")

# ----------------------------------------------------------
# MAIN FUNCTION: CREATE TENDER DIRECTORY
# ----------------------------------------------------------
def create_tender_folder(base_dir: str, ref: str, client: str, short_title: str) -> str:
    """
    Creates tender directory:
    MASTER/TENDERS/02_Active_Tenders/[Ref]_[Client]_[ShortTitle]/
    And all subfolders.
    """

    # Clean components
    ref = clean_name(ref) if ref else "REF"
    client = clean_name(client) if client else "CLIENT"
    short_title = clean_name(short_title) if short_title else "Tender"

    folder_name = f"{ref}_{client}_{short_title}"
    tender_path = os.path.join(base_dir, folder_name)

    # If folder already exists → return it
    if os.path.exists(tender_path):
        return tender_path

    # Create main tender folder
    os.makedirs(tender_path, exist_ok=True)

    # Create subfolders
    subfolders = [
        "01_Advert",
        "02_Documents",
        "03_Clarifications",
        "04_Technical",
        "05_Pricing",
        "06_Compliance",
        "07_Final",
        "Partners"
    ]

    for sub in subfolders:
        os.makedirs(os.path.join(tender_path, sub), exist_ok=True)

    return tender_path

# ----------------------------------------------------------
# LOG FOLDER CREATION EVENTS
# ----------------------------------------------------------
def folder_creation_log(log_path: str, tender_name: str, folder_path: str):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as log_file:
        log_file.write(f"[{timestamp}] Folder created for tender: {tender_name} → {folder_path}\n")
