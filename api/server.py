from __future__ import annotations

import csv
import json
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, status
from fastapi.security import APIKeyHeader
from pydantic import BaseModel

from core.logger import logger
from core.review_generator import generate_reviews
from core.queue_manager import JobQueueManager
from core import database

# Load settings and API token
SETTINGS_PATH = Path("config/settings.json")
settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
API_TOKEN = settings.get("api_token")

api_key_header = APIKeyHeader(name="X-API-Token", auto_error=False)


def verify_token(token: str = Depends(api_key_header)) -> None:
    if API_TOKEN and token != API_TOKEN:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid API token")


app = FastAPI()
queue_manager = JobQueueManager()


class ReviewRequest(BaseModel):
    prompt: str
    tone: str | None = None


class SubmitReviewRequest(BaseModel):
    site: str
    template: str | None = None
    review_text: str
    proxy_id: int | None = None
    account_id: int | None = None


@app.post("/generate_review")
def generate_review(data: ReviewRequest, _: None = Depends(verify_token)):
    logger.info("API generate_review called")
    prompt = data.prompt
    if data.tone:
        prompt = f"{prompt} Tone:{data.tone}"
    review = generate_reviews(prompt, count=1)[0]
    return {"review": review}


@app.get("/log")
def get_log(_: None = Depends(verify_token)):
    logger.info("API log requested")
    log_path = Path("output/post_log.csv")
    if not log_path.exists():
        return []
    with log_path.open("r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        return list(reader)


@app.get("/status")
def status_endpoint(_: None = Depends(verify_token)):
    logger.info("API status requested")
    job_counts = database.job_counts()
    queue_length = sum(job_counts.values())
    pending_jobs = job_counts.get("Pending", 0)
    account_health = database.accounts_status_counts()
    proxy_health = database.proxies_status_counts()
    return {
        "queue_length": queue_length,
        "pending_jobs": pending_jobs,
        "account_health": account_health,
        "proxy_health": proxy_health,
    }


@app.post("/submit_review")
def submit_review(req: SubmitReviewRequest, _: None = Depends(verify_token)):
    logger.info("API submit_review called")
    job_id = queue_manager.add_job(
        req.site,
        req.review_text,
        proxy_id=req.proxy_id,
        account_id=req.account_id,
    )
    return {"job_id": job_id}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("api.server:app", host="0.0.0.0", port=8000, reload=False)

