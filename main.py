import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import RedirectResponse

from db import init_db
from logging_config import setup_logging
from routes import router

setup_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    logger.info("Application started")
    yield
    logger.info("Application stopped")


app = FastAPI(title="Simple LLM API", lifespan=lifespan)


@app.get("/", include_in_schema=False)
def root():
    return RedirectResponse("/docs")


app.include_router(router)
