import pytest
from packages.db.vector import MemoryRepository

@pytest.mark.asyncio
async def test_memory_repo_exposes_tenant_scoped_search():
    assert hasattr(MemoryRepository, "lexical_search")
