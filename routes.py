"""HTTP endpoints."""

import logging

from fastapi import APIRouter

from llm import ask_model
from schemas import AskRequest, AskResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    logger.info("POST /ask received")
    return AskResponse(answer=ask_model(req.question))
