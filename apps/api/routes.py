from fastapi import APIRouter
from packages.observability.metrics import RunMetrics

router = APIRouter(prefix="/v1")
metrics = RunMetrics()

@router.get("/system/metrics")
async def system_metrics():
    return metrics.snapshot()
