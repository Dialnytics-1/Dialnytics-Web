CREATE TABLE IF NOT EXISTS mkt_addon_entitlement_jobs (
 order_reference VARCHAR(32) PRIMARY KEY,
 account_id VARCHAR(100) NOT NULL,
 paid_through DATE NOT NULL,
 status VARCHAR(20) NOT NULL DEFAULT 'pending',
 attempts INTEGER NOT NULL DEFAULT 0,
 next_attempt TIMESTAMPTZ NOT NULL DEFAULT NOW(),
 completed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mkt_addon_entitlement_status ON mkt_addon_entitlement_jobs(status, next_attempt);
