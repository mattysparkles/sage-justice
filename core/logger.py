
import logging
from logging.handlers import RotatingFileHandler
import os

LOG_DIR = "logs"
LOG_FILE = os.path.join(LOG_DIR, "app.log")

def setup_logger():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR)

    logger = logging.getLogger("SageJusticeLogger")
    logger.setLevel(logging.DEBUG)

    handler = RotatingFileHandler(LOG_FILE, maxBytes=1_000_000, backupCount=3)
    formatter = logging.Formatter('%(asctime)s [%(levelname)s] %(message)s')
    handler.setFormatter(formatter)
    logger.addHandler(handler)

    return logger

logger = setup_logger()
