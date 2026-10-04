from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, Identity, Integer, JSON, String, Text, UniqueConstraint
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

class Base(DeclarativeBase):
    pass

class RunRecord(Base):
    __tablename__ = "runs"
    __table_args__ = (
        UniqueConstraint("tenant_id", "idempotency_key", name="uq_runs_tenant_idempotency"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    state: Mapped[str] = mapped_column(String(32), default="created", index=True)
    prompt: Mapped[str] = mapped_column(Text)
    model: Mapped[str] = mapped_column(String(256), default="reasoning-default")
    reasoning_effort: Mapped[str] = mapped_column(String(32), default="medium")
    checkpoint: Mapped[dict] = mapped_column(JSON, default=dict)
    attempts: Mapped[int] = mapped_column(Integer, default=0)
    idempotency_key: Mapped[str | None] = mapped_column(String(256), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    sequence: Mapped[int] = mapped_column(BigInteger, Identity(), unique=True, index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    run_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    event_type: Mapped[str] = mapped_column(String(128), index=True)
    actor: Mapped[str] = mapped_column(String(256))
    payload: Mapped[dict] = mapped_column(JSON, default=dict)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )


class ToolActionRecord(Base):
    __tablename__ = "tool_action_records"
    __table_args__ = (UniqueConstraint("tenant_id", "action_id", name="uq_tool_action_tenant_action"),)
    id: Mapped[UUID] = mapped_column(primary_key=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    run_id: Mapped[UUID | None] = mapped_column(index=True, nullable=True)
    action_id: Mapped[str] = mapped_column(String(64))
    tool: Mapped[str] = mapped_column(String(256))
    status: Mapped[str] = mapped_column(String(32), index=True)
    idempotent: Mapped[bool] = mapped_column(default=True)
    output: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
    completed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
