-- Apply only after reviewing production schema and backup.
CREATE TABLE IF NOT EXISTS mkt_signup_secrets (
  order_reference VARCHAR(128) PRIMARY KEY,
  encrypted_payload BYTEA NOT NULL,
  expires_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mkt_signup_secrets_expires_at ON mkt_signup_secrets (expires_at);
