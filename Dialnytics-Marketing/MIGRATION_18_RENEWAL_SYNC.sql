-- Marketing PostgreSQL ONLY. Back up first. Not for the dialer database.
CREATE TABLE IF NOT EXISTS mkt_renewal_sync_jobs (
    account_id VARCHAR(100) PRIMARY KEY,
    status VARCHAR(20) NOT NULL DEFAULT 'pending',
    target_paid_through TIMESTAMPTZ NOT NULL,
    attempts INTEGER NOT NULL DEFAULT 0,
    next_attempt TIMESTAMPTZ NOT NULL,
    lease_until TIMESTAMPTZ,
    last_error VARCHAR(200) NOT NULL DEFAULT ''
);
CREATE INDEX IF NOT EXISTS ix_mkt_renewal_sync_status_due
    ON mkt_renewal_sync_jobs(status, next_attempt);
