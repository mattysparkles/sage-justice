
import schedule
import time
import threading
from core.logger import logger

class Scheduler:
    def __init__(self):
        self.jobs = []
        self._stop_event = threading.Event()

    def schedule_review_post(self, func, interval_minutes=5):
        logger.info(f"Scheduling review job every {interval_minutes} minutes")
        job = schedule.every(interval_minutes).minutes.do(func)
        self.jobs.append(job)

    def run(self):
        def loop():
            while not self._stop_event.is_set():
                schedule.run_pending()
                time.sleep(1)
        self.thread = threading.Thread(target=loop, daemon=True)
        self.thread.start()
        logger.info("Scheduler started.")

    def stop(self):
        self._stop_event.set()
        self.thread.join()
        logger.info("Scheduler stopped.")
