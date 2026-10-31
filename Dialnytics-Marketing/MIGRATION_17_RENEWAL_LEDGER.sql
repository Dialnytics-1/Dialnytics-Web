-- Run on the MARKETING PostgreSQL database only, after backup.
-- Do not apply to dialer/Supabase database.
CREATE TABLE IF NOT EXISTS mkt_subscription_terms (
    account_id VARCHAR(100) PRIMARY KEY,
    paid_through TIMESTAMPTZ NOT NULL,
    last_payment_id VARCHAR(200) NOT NULL,
    renewal_count INTEGER NOT NULL DEFAULT 0
);
CREATE TABLE IF NOT EXISTS mkt_renewal_receipts (
    payment_id VARCHAR(200) PRIMARY KEY,
    account_id VARCHAR(100) NOT NULL,
    paid_through TIMESTAMPTZ NOT NULL,
    confirmed_at TIMESTAMPTZ NOT NULL
);
CREATE INDEX IF NOT EXISTS ix_mkt_renewal_receipts_account_id
    ON mkt_renewal_receipts(account_id);
