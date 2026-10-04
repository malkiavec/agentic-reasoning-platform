from datetime import datetime, timezone
from uuid import UUID, uuid4

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from packages.db.models import Base

class ApprovalRecord(Base):
    __tablename__ = "approvals"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    run_id: Mapped[UUID] = mapped_column(index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    action: Mapped[str] = mapped_column(Text)
    action_hash: Mapped[str] = mapped_column(String(64), index=True)
    risk: Mapped[str] = mapped_column(String(32))
    status: Mapped[str] = mapped_column(String(32), default="pending", index=True)
    required_approvers: Mapped[int] = mapped_column(Integer, default=1)
    approvals_received: Mapped[int] = mapped_column(Integer, default=0)
    expires_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))

class ApprovalDecisionRecord(Base):
    __tablename__ = "approval_decisions"
    __table_args__ = (
        UniqueConstraint("approval_id", "approver_subject", name="uq_approval_approver"),
    )
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    approval_id: Mapped[UUID] = mapped_column(index=True)
    tenant_id: Mapped[str] = mapped_column(String(128), index=True)
    approver_subject: Mapped[str] = mapped_column(String(256))
    decision: Mapped[str] = mapped_column(String(16))
    comment: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(timezone.utc))
