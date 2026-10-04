from sqlalchemy.ext.asyncio import AsyncEngine
from packages.db.models import Base
from packages.db.memory_models import MemoryRecord
from packages.db.approval_models import ApprovalRecord

# Explicit imports above ensure every ORM model is registered before metadata creation.
async def create_schema(engine: AsyncEngine) -> None:
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
