from datetime import datetime, timezone
from uuid import UUID
from packages.hitl.persistent import create_approval, get_approval

class PersistentApprovalService:
    def __init__(self, session_factory, ttl_seconds:int=900):
        self.session_factory=session_factory
        self.ttl_seconds=ttl_seconds

    async def request(self, *, run_id:str, tenant_id:str, actor:str, tool:str, arguments:dict, risk:str):
        from datetime import timedelta
        import json
        async with self.session_factory() as session:
            return await create_approval(session,run_id=UUID(run_id),tenant_id=tenant_id,
                action=json.dumps({"tool":tool,"arguments":arguments},separators=(",",":")),
                risk=risk,status="pending",required_approvers=1,approvals_received=0,
                expires_at=datetime.now(timezone.utc)+timedelta(seconds=self.ttl_seconds))

    async def verify(self, *, approval_id:str|None, run_id:str|None, tenant_id:str,
                     tool:str, arguments:dict) -> bool:
        if not approval_id or not run_id:
            return False
        import json
        async with self.session_factory() as session:
            record=await get_approval(session,UUID(approval_id))
            if record is None or record.status!="approved":
                return False
            if record.tenant_id!=tenant_id or record.run_id!=UUID(run_id):
                return False
            try:
                action=json.loads(record.action)
            except (TypeError,ValueError):
                return False
            return action.get("tool")==tool and action.get("arguments")==arguments
