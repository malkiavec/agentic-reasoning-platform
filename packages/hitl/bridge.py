from datetime import datetime, timedelta, timezone
from uuid import UUID
from packages.hitl.persistent import create_approval

class PersistentApprovalService:
    def __init__(self, session_factory, ttl_seconds:int=900):
        self.session_factory=session_factory
        self.ttl_seconds=ttl_seconds

    async def request(self, *, run_id:str, tenant_id:str, actor:str, tool:str,
                      arguments:dict, risk:str):
        async with self.session_factory() as session:
            return await create_approval(session,run_id=UUID(run_id),tenant_id=tenant_id,
                action=tool,risk=risk,status="pending",required_approvers=1,
                approvals_received=0,
                expires_at=datetime.now(timezone.utc)+timedelta(seconds=self.ttl_seconds))
