-- Durable tool action ledger.
CREATE TABLE IF NOT EXISTS tool_action_records (
    id UUID PRIMARY KEY,
    tenant_id VARCHAR(128) NOT NULL,
    run_id UUID NULL,
    action_id VARCHAR(64) NOT NULL,
    tool VARCHAR(256) NOT NULL,
    status VARCHAR(32) NOT NULL,
    idempotent BOOLEAN NOT NULL DEFAULT TRUE,
    output JSONB NULL,
    error TEXT NULL,
    created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
    completed_at TIMESTAMPTZ NULL,
    CONSTRAINT uq_tool_action_tenant_action UNIQUE (tenant_id, action_id)
);
CREATE INDEX IF NOT EXISTS ix_tool_action_run ON tool_action_records(tenant_id, run_id);
CREATE INDEX IF NOT EXISTS ix_tool_action_status ON tool_action_records(status);
