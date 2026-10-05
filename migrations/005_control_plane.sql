-- 005: tenant policy, budgets and integration configuration
CREATE TABLE IF NOT EXISTS tenant_policies (
  tenant_id VARCHAR(128) PRIMARY KEY,
  policy JSONB NOT NULL DEFAULT '{}'::jsonb,
  updated_by VARCHAR(256) NOT NULL DEFAULT 'system',
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_budgets (
  tenant_id VARCHAR(128) PRIMARY KEY,
  monthly_run_limit BIGINT NOT NULL DEFAULT 10000 CHECK (monthly_run_limit > 0),
  monthly_tool_call_limit BIGINT NOT NULL DEFAULT 100000 CHECK (monthly_tool_call_limit > 0),
  monthly_token_limit BIGINT NOT NULL DEFAULT 100000000 CHECK (monthly_token_limit > 0),
  monthly_cost_limit_micros BIGINT NOT NULL DEFAULT 1000000000 CHECK (monthly_cost_limit_micros > 0),
  used_runs BIGINT NOT NULL DEFAULT 0,
  used_tool_calls BIGINT NOT NULL DEFAULT 0,
  used_tokens BIGINT NOT NULL DEFAULT 0,
  used_cost_micros BIGINT NOT NULL DEFAULT 0,
  period_start DATE NOT NULL DEFAULT CURRENT_DATE,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS tenant_integrations (
  tenant_id VARCHAR(128) NOT NULL,
  tool_name VARCHAR(128) NOT NULL,
  enabled BOOLEAN NOT NULL DEFAULT FALSE,
  config JSONB NOT NULL DEFAULT '{}'::jsonb,
  credential_ref VARCHAR(512),
  updated_by VARCHAR(256) NOT NULL,
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, tool_name)
);
CREATE INDEX IF NOT EXISTS ix_tenant_integrations_tool ON tenant_integrations(tool_name);
