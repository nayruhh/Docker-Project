"""Gemini client and the function that asks it a question."""

import logging
import os

from dotenv import load_dotenv
from fastapi import HTTPException
from openai import APITimeoutError, AuthenticationError, OpenAI, OpenAIError, RateLimitError

load_dotenv()
logger = logging.getLogger(__name__)

MODEL = os.getenv("GEMINI_MODEL", "gemini-3.5-flash")

# Gemini exposes an OpenAI-compatible endpoint, so the openai SDK works as is.
client = OpenAI(
    api_key=os.getenv("GEMINI_API_KEY"),
    base_url="https://generativelanguage.googleapis.com/v1beta/openai/",
    timeout=30,
    max_retries=1,
)


def ask_model(question: str) -> str:
    """Send the question to the model and return the answer, or raise HTTPException."""
    logger.info("Asking model %s (question length=%d)", MODEL, len(question))
    try:
        res = client.chat.completions.create(
            model=MODEL,
            messages=[{"role": "user", "content": question}],
        )
    except APITimeoutError as e:
        logger.error("Model request timed out")
        raise HTTPException(status_code=504, detail="The model took too long to respond.") from e
    except RateLimitError as e:
        logger.warning("Model rate limit or quota reached")
        raise HTTPException(status_code=429, detail="Model rate limit or quota reached.") from e
    except AuthenticationError as e:
        logger.error("Authentication with the model provider failed")
        raise HTTPException(status_code=502, detail="Invalid or missing GEMINI_API_KEY.") from e
    except OpenAIError as e:
        logger.exception("Unexpected model error")
        raise HTTPException(status_code=502, detail=f"Model error: {e}") from e

    answer = (res.choices[0].message.content or "").strip() if res.choices else ""
    if not answer:
        logger.error("Model returned an empty answer")
        raise HTTPException(status_code=502, detail="Model returned an empty answer.")
    logger.info("Model answered (answer length=%d)", len(answer))
    return answer
