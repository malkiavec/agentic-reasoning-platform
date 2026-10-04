-- 003: explicit tenant membership and role binding
CREATE TABLE IF NOT EXISTS tenant_memberships (
  tenant_id VARCHAR(128) NOT NULL,
  subject VARCHAR(256) NOT NULL,
  roles JSONB NOT NULL DEFAULT '[]'::jsonb,
  active BOOLEAN NOT NULL DEFAULT TRUE,
  created_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (tenant_id, subject)
);
CREATE INDEX IF NOT EXISTS ix_tenant_memberships_subject ON tenant_memberships(subject);
CREATE INDEX IF NOT EXISTS ix_tenant_memberships_active ON tenant_memberships(tenant_id, active);
