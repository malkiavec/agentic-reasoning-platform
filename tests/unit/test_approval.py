import pytest
from datetime import datetime, timedelta, timezone
from packages.db.approval_models import ApprovalRecord
from packages.hitl.service import ApprovalService

def test_memory_approval_expires():
    service = ApprovalService()
    item = service.request(__import__("uuid").uuid4(), "t1", "shell", "HIGH", ttl_seconds=1)
    assert item.approved is None
