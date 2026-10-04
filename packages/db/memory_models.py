from datetime import datetime, timezone
from uuid import UUID, uuid4
from sqlalchemy import DateTime, Float, JSON, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from packages.db.models import Base

class MemoryRecord(Base):
    __tablename__ = "memory_records"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    kind: Mapped[str] = mapped_column(String(32), index=True)
    content: Mapped[str] = mapped_column(Text)
    source: Mapped[str] = mapped_column(String(512))
    confidence: Mapped[float] = mapped_column(Float, default=1.0)
    metadata: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
