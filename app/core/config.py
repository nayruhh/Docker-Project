"""Settings read from environment variables (and .env for local runs)."""

import os

from dotenv import load_dotenv
from sqlalchemy.engine import URL

load_dotenv()

DRIVER = "postgresql+psycopg"


def get_database_url() -> str | None:
    """Build the SQLAlchemy database URL, or return None if no database is configured.

    1. DATABASE_URL, if set (plain ``postgresql://`` URLs are accepted too).
    2. Otherwise the parts POSTGRES_HOST / PORT / USER / PASSWORD / DB. Docker Compose uses
       this form so special characters in the password never need URL-encoding.
    """
    url = os.getenv("DATABASE_URL")
    if url:
        for prefix in ("postgresql://", "postgres://"):
            if url.startswith(prefix):
                return DRIVER + "://" + url[len(prefix) :]
        return url

    host = os.getenv("POSTGRES_HOST")
    if not host:
        return None
    return URL.create(
        DRIVER,
        username=os.getenv("POSTGRES_USER"),
        password=os.getenv("POSTGRES_PASSWORD"),
        host=host,
        port=int(os.getenv("POSTGRES_PORT", "5432")),
        database=os.getenv("POSTGRES_DB"),
    ).render_as_string(hide_password=False)
