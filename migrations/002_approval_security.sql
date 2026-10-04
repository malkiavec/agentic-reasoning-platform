-- 002: approval action binding and decision history
ALTER TABLE approvals ADD COLUMN IF NOT EXISTS action_hash VARCHAR(64);
UPDATE approvals
SET action_hash = encode(sha256(convert_to(action, 'UTF8')), 'hex')
WHERE action_hash IS NULL;
ALTER TABLE approvals ALTER COLUMN action_hash SET NOT NULL;
CREATE INDEX IF NOT EXISTS ix_approvals_action_hash ON approvals(action_hash);

CREATE TABLE IF NOT EXISTS approval_decisions (
  id UUID PRIMARY KEY,
  approval_id UUID NOT NULL,
  tenant_id VARCHAR(128) NOT NULL,
  approver_subject VARCHAR(256) NOT NULL,
  decision VARCHAR(16) NOT NULL,
  comment TEXT NOT NULL DEFAULT '',
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  CONSTRAINT uq_approval_approver UNIQUE (approval_id, approver_subject)
);
CREATE INDEX IF NOT EXISTS ix_approval_decisions_approval_id ON approval_decisions(approval_id);
CREATE INDEX IF NOT EXISTS ix_approval_decisions_tenant_id ON approval_decisions(tenant_id);
