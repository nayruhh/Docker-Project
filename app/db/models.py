"""Database models."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Text, false, func, text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


class Base(DeclarativeBase):
    pass


class QARecord(Base):
    """One submitted question and the answer that was returned for it.

    One row per submission (see docs/DESIGN.md for why this is a single table and why
    repeated questions get a new row each time).
    """

    __tablename__ = "qa_records"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid.uuid4,
        server_default=text("gen_random_uuid()"),
    )
    # The question exactly as submitted (leading/trailing spaces trimmed).
    question: Mapped[str] = mapped_column(Text, nullable=False)
    # Lower-cased, whitespace-collapsed copy; this is what the cache key is built from.
    normalized_question: Mapped[str] = mapped_column(Text, nullable=False)
    answer: Mapped[str] = mapped_column(Text, nullable=False)
    # True when the answer came from Redis instead of being generated.
    cache_hit: Mapped[bool] = mapped_column(
        Boolean, nullable=False, default=False, server_default=false()
    )
    # Indexed because history is always read newest-first.
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), nullable=False, server_default=func.now(), index=True
    )
