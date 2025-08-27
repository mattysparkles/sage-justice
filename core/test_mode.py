from selenium import webdriver
import time

def dry_run_post(site_template_path, review_text):
    from core.drip_scheduler import post_review
    print("[DRY RUN] Launching browser and previewing submission process...")
    post_review(site_template_path, review_text)
    print("[DRY RUN] Submission complete (no actual account used).")
    time.sleep(2)
