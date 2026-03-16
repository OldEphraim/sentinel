import uuid
from datetime import datetime
from sqlalchemy import String, DateTime, Float, Text, JSON
from sqlalchemy.orm import Mapped, mapped_column
from src.database import Base


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[str] = mapped_column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    watch_id: Mapped[str] = mapped_column(String, nullable=False)
    skyfi_order_id: Mapped[str | None] = mapped_column(String, nullable=True)
    skyfi_archive_id: Mapped[str | None] = mapped_column(String, nullable=True)
    status: Mapped[str] = mapped_column(String(50), nullable=False, default="pending")
    sensor_type: Mapped[str] = mapped_column(String(100), nullable=False)
    analytics_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cost_usd: Mapped[float | None] = mapped_column(Float, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
    answer: Mapped[str | None] = mapped_column(Text, nullable=True)
    confidence: Mapped[str | None] = mapped_column(String(20), nullable=True)
    evidence: Mapped[list | None] = mapped_column(JSON, nullable=True)
    raw_analytics: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    imagery_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    captured_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    agent_thoughts: Mapped[list | None] = mapped_column(JSON, nullable=True)
