
import time
from functools import wraps
from core.logger import logger

def retry(max_attempts=3, delay=2, backoff=2):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            wait = delay
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    logger.warning(f"Attempt {attempts} failed: {e}")
                    if attempts == max_attempts:
                        logger.error(f"Max attempts reached. Giving up on {func.__name__}.")
                        raise
                    time.sleep(wait)
                    wait *= backoff
        return wrapper
    return decorator
