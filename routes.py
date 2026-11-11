"""HTTP endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query, Response

from cache import get_cached, set_cached
from db import get_history, save_qa
from llm import ask_model
from schemas import AskRequest, AskResponse, HistoryItem

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, response: Response):
    logger.info("POST /ask received")
    answer = get_cached(req.question)
    if answer is not None:
        logger.info("Cache hit")
        response.headers["X-Cache"] = "HIT"
    else:
        logger.info("Cache miss")
        answer = ask_model(req.question)
        set_cached(req.question, answer)
        response.headers["X-Cache"] = "MISS"
    save_qa(req.question, answer)
    return AskResponse(answer=answer)


@router.get("/history", response_model=list[HistoryItem])
def history(limit: int = Query(20, ge=1, le=100, description="How many rows to return.")):
    logger.info("GET /history received (limit=%d)", limit)
    try:
        return get_history(limit)
    except Exception as e:
        logger.error("Could not read history: %s", e)
        raise HTTPException(status_code=503, detail="Database unavailable.") from e
