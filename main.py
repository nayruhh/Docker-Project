import logging

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from logging_config import setup_logging

setup_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Simple LLM API")


@app.on_event("startup")
def on_startup() -> None:
    logger.info("Application started")


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")
