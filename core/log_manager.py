import csv
import os
from datetime import datetime

LOG_FILE = "output/post_log.csv"

def log_post(site, review_text, success=True, message=""):
    os.makedirs(os.path.dirname(LOG_FILE), exist_ok=True)
    with open(LOG_FILE, mode="a", newline="", encoding="utf-8") as file:
        writer = csv.writer(file)
        writer.writerow([datetime.utcnow().isoformat(), site, "SUCCESS" if success else "FAIL", review_text, message])
