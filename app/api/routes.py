"""HTTP endpoints."""

import logging

from fastapi import APIRouter, HTTPException, Query, Response

from app.api.schemas import AskRequest, AskResponse, HistoryItem
from app.db.crud import get_history, save_qa
from app.services.cache import get_cached, set_cached
from app.services.llm import ask_model

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest, response: Response):
    """Answer a question, using Redis to skip generation for repeated questions.

    HIT:  return the cached answer (no generation), but still record this submission.
    MISS: generate the answer -> save it in PostgreSQL -> cache it in Redis -> return it.
    Redis problems count as a MISS, so the API keeps working without it.
    """
    logger.info("POST /ask received")
    question = req.question

    cached = get_cached(question)
    if cached is not None:
        logger.info("Cache hit")
        response.headers["X-Cache"] = "HIT"
        save_qa(question, cached, cache_hit=True)
        return AskResponse(answer=cached)

    logger.info("Cache miss")
    response.headers["X-Cache"] = "MISS"
    answer = ask_model(question)
    save_qa(question, answer, cache_hit=False)
    set_cached(question, answer)
    return AskResponse(answer=answer)


@router.get("/history", response_model=list[HistoryItem])
def history(limit: int = Query(20, ge=1, le=100, description="How many rows to return.")):
    logger.info("GET /history received (limit=%d)", limit)
    try:
        return get_history(limit)
    except Exception as e:
        logger.error("Could not read history: %s", e)
        raise HTTPException(status_code=503, detail="Database unavailable.") from e
