import time
import random
from datetime import timedelta

def drip_feed(reviews, interval_range=(2, 5)):
    for review in reviews:
        print(f"Posting review: {review[:60]}...")
        # Simulate post
        time.sleep(random.randint(*interval_range))
