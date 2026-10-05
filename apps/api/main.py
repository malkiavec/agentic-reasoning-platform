import os
import time
from uuid import UUID
from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
from redis.asyncio import Redis
from sqlalchemy import text
from pydantic import BaseModel, Field
from packages.db.repository import create_run, get_run
from packages.db.session import SessionLocal
from packages.security.quota import QuotaExceeded, reserve_run
from apps.worker.tasks import execute_run
from apps.api.websocket import router as websocket_router
from apps.api.approvals import router as approval_router
from apps.api.routes import router as api_router
from apps.api.auth import RequestPrincipal, require_principal

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    from opentelemetry import trace
    from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
    from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    _provider=TracerProvider(resource=Resource.create({"service.name":os.getenv("OTEL_SERVICE_NAME","agentic-api")}))
    _provider.add_span_processor(BatchSpanProcessor(OTLPSpanExporter()))
    trace.set_tracer_provider(_provider)

app=FastAPI(title="Agentic Reasoning Platform API",version="0.5.0")
origins=[x.strip() for x in os.getenv("CORS_ORIGINS","").split(",") if x.strip()]
app.add_middleware(CORSMiddleware,allow_origins=origins,allow_credentials=True,allow_methods=["GET","POST","PUT","PATCH","DELETE","OPTIONS"],allow_headers=["Authorization","Content-Type","X-Request-ID"])

@app.middleware("http")
async def distributed_rate_limit(request:Request,call_next):
    if request.url.path in {"/health","/ready","/metrics"}: return await call_next(request)
    redis=None; client=request.headers.get("x-forwarded-for",request.client.host if request.client else "unknown").split(",")[0].strip()
    key=f"agent:http:rate:{client}:{int(time.time()//60)}"
    try:
        redis=Redis.from_url(os.getenv("REDIS_URL","redis://redis:6379/0"),decode_responses=True); count=await redis.incr(key)
        if count==1: await redis.expire(key,120)
        if count>int(os.getenv("API_RATE_LIMIT_PER_MINUTE","120")): return JSONResponse({"detail":"rate_limit_exceeded"},status_code=429,headers={"Retry-After":"60"})
        return await call_next(request)
    except Exception:
        if os.getenv("APP_ENV","production").lower() in {"production","prod"}: return JSONResponse({"detail":"rate_limit_dependency_unavailable"},status_code=503)
        return await call_next(request)
    finally:
        if redis is not None: await redis.aclose()

if os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT"):
    FastAPIInstrumentor.instrument_app(app); SQLAlchemyInstrumentor().instrument()
app.include_router(websocket_router); app.include_router(approval_router); app.include_router(api_router)

class RunRequest(BaseModel):
    prompt:str=Field(min_length=1,max_length=200000)
    tenant_id:str|None=Field(default=None,min_length=1,max_length=128)
    model:str|None=None
    reasoning_effort:str="medium"
    max_steps:int=Field(default=20,ge=1,le=200)
    idempotency_key:str|None=Field(default=None,max_length=256)
class RunResponse(BaseModel):
    run_id:str
    status:str
    message:str

@app.get("/health")
async def health(): return {"status":"ok"}

@app.get("/ready")
async def ready():
    redis=None
    try:
        async with SessionLocal() as s: await s.execute(text("SELECT 1"))
        redis=Redis.from_url(os.getenv("REDIS_URL","redis://redis:6379/0")); await redis.ping()
    except Exception as exc: raise HTTPException(503,"dependencies_unready") from exc
    finally:
        if redis is not None: await redis.aclose()
    return {"status":"ready"}

@app.post("/v1/runs",response_model=RunResponse)
async def create_agent_run(request:RunRequest,principal:RequestPrincipal=Depends(require_principal)):
    if request.tenant_id is not None and request.tenant_id!=principal.tenant_id: raise HTTPException(403,"tenant_mismatch")
    async with SessionLocal() as s:
        try: await reserve_run(s,principal.tenant_id)
        except QuotaExceeded as exc: raise HTTPException(429,str(exc)) from exc
        record=await create_run(s,tenant_id=principal.tenant_id,prompt=request.prompt,model=request.model or "reasoning-default",reasoning_effort=request.reasoning_effort,idempotency_key=request.idempotency_key,checkpoint={"max_steps":request.max_steps})
    execute_run.delay(str(record.id))
    return RunResponse(run_id=str(record.id),status="accepted",message="Run queued")

@app.get("/v1/runs/{run_id}")
async def get_agent_run(run_id:UUID,principal:RequestPrincipal=Depends(require_principal)):
    async with SessionLocal() as s:
        record=await get_run(s,run_id)
        if record is None or record.tenant_id!=principal.tenant_id: raise HTTPException(404,"run_not_found")
        return {"run_id":str(record.id),"state":record.state,"checkpoint":record.checkpoint,"attempts":record.attempts}
