from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class QuotaExceeded(RuntimeError): pass

async def ensure_budget(session:AsyncSession,tenant_id:str)->None:
    await session.execute(text("""
      INSERT INTO tenant_budgets(tenant_id) VALUES(:tenant)
      ON CONFLICT(tenant_id) DO UPDATE SET
        used_runs=CASE WHEN tenant_budgets.period_start < date_trunc('month',CURRENT_DATE)::date THEN 0 ELSE tenant_budgets.used_runs END,
        used_tool_calls=CASE WHEN tenant_budgets.period_start < date_trunc('month',CURRENT_DATE)::date THEN 0 ELSE tenant_budgets.used_tool_calls END,
        used_tokens=CASE WHEN tenant_budgets.period_start < date_trunc('month',CURRENT_DATE)::date THEN 0 ELSE tenant_budgets.used_tokens END,
        used_cost_micros=CASE WHEN tenant_budgets.period_start < date_trunc('month',CURRENT_DATE)::date THEN 0 ELSE tenant_budgets.used_cost_micros END,
        period_start=CASE WHEN tenant_budgets.period_start < date_trunc('month',CURRENT_DATE)::date THEN date_trunc('month',CURRENT_DATE)::date ELSE tenant_budgets.period_start END,
        updated_at=now()
    """),{"tenant":tenant_id})

async def reserve_run(session:AsyncSession,tenant_id:str)->None:
    await ensure_budget(session,tenant_id)
    row=(await session.execute(text("""
      UPDATE tenant_budgets SET used_runs=used_runs+1,updated_at=now()
      WHERE tenant_id=:tenant AND used_runs < monthly_run_limit
      RETURNING used_runs,monthly_run_limit
    """),{"tenant":tenant_id})).mappings().first()
    if row is None: raise QuotaExceeded("run_budget_exceeded")

async def reserve_tool_call(session:AsyncSession,tenant_id:str,tokens:int=0,cost_micros:int=0)->None:
    await ensure_budget(session,tenant_id)
    row=(await session.execute(text("""
      UPDATE tenant_budgets SET used_tool_calls=used_tool_calls+1,used_tokens=used_tokens+:tokens,
        used_cost_micros=used_cost_micros+:cost,updated_at=now()
      WHERE tenant_id=:tenant AND used_tool_calls+1<=monthly_tool_call_limit
        AND used_tokens+:tokens<=monthly_token_limit
        AND used_cost_micros+:cost<=monthly_cost_limit_micros
      RETURNING used_tool_calls
    """),{"tenant":tenant_id,"tokens":tokens,"cost":cost_micros})).first()
    if row is None: raise QuotaExceeded("tool_budget_exceeded")
