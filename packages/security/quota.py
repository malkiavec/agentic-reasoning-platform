from datetime import date
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

class QuotaExceeded(RuntimeError):
    pass

async def ensure_budget(session: AsyncSession, tenant_id: str) -> None:
    await session.execute(text("""
        INSERT INTO tenant_budgets (tenant_id) VALUES (:tenant)
        ON CONFLICT (tenant_id) DO UPDATE SET
          used_runs = CASE WHEN period_start < CURRENT_DATE - INTERVAL '30 days' THEN 0 ELSE tenant_budgets.used_runs END,
          used_tool_calls = CASE WHEN period_start < CURRENT_DATE - INTERVAL '30 days' THEN 0 ELSE tenant_budgets.used_tool_calls END,
          used_tokens = CASE WHEN period_start < CURRENT_DATE - INTERVAL '30 days' THEN 0 ELSE tenant_budgets.used_tokens END,
          used_cost_micros = CASE WHEN period_start < CURRENT_DATE - INTERVAL '30 days' THEN 0 ELSE tenant_budgets.used_cost_micros END,
          period_start = CASE WHEN period_start < CURRENT_DATE - INTERVAL '30 days' THEN CURRENT_DATE ELSE tenant_budgets.period_start END
    """), {"tenant": tenant_id})
    row = (await session.execute(text("""
        SELECT monthly_run_limit, monthly_tool_call_limit, monthly_token_limit,
               monthly_cost_limit_micros, used_runs, used_tool_calls, used_tokens, used_cost_micros
        FROM tenant_budgets WHERE tenant_id=:tenant FOR UPDATE
    """), {"tenant": tenant_id})).mappings().one()
    if row["used_runs"] >= row["monthly_run_limit"]:
        raise QuotaExceeded("run_budget_exceeded")

async def reserve_run(session: AsyncSession, tenant_id: str) -> None:
    await ensure_budget(session, tenant_id)
    await session.execute(text("""
        UPDATE tenant_budgets SET used_runs=used_runs+1, updated_at=now()
        WHERE tenant_id=:tenant AND used_runs < monthly_run_limit
    """), {"tenant": tenant_id})
    if (await session.execute(text("SELECT used_runs, monthly_run_limit FROM tenant_budgets WHERE tenant_id=:tenant"), {"tenant":tenant_id})).one().used_runs > (await session.execute(text("SELECT monthly_run_limit FROM tenant_budgets WHERE tenant_id=:tenant"), {"tenant":tenant_id})).one().monthly_run_limit:
        raise QuotaExceeded("run_budget_exceeded")

async def reserve_tool_call(session: AsyncSession, tenant_id: str, tokens: int = 0, cost_micros: int = 0) -> None:
    await ensure_budget(session, tenant_id)
    row=(await session.execute(text("""
      SELECT monthly_tool_call_limit,monthly_token_limit,monthly_cost_limit_micros,used_tool_calls,used_tokens,used_cost_micros
      FROM tenant_budgets WHERE tenant_id=:tenant FOR UPDATE
    """),{"tenant":tenant_id})).mappings().one()
    if row["used_tool_calls"]+1>row["monthly_tool_call_limit"] or row["used_tokens"]+tokens>row["monthly_token_limit"] or row["used_cost_micros"]+cost_micros>row["monthly_cost_limit_micros"]:
        raise QuotaExceeded("tool_budget_exceeded")
    await session.execute(text("""
      UPDATE tenant_budgets SET used_tool_calls=used_tool_calls+1,used_tokens=used_tokens+:tokens,
      used_cost_micros=used_cost_micros+:cost,updated_at=now() WHERE tenant_id=:tenant
    """),{"tenant":tenant_id,"tokens":tokens,"cost":cost_micros})
