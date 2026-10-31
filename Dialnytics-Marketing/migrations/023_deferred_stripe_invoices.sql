-- Apply to the MARKETING PostgreSQL database before deploying v23.
CREATE TABLE IF NOT EXISTS mkt_deferred_stripe_invoices (
  invoice_id VARCHAR(100) PRIMARY KEY,
  subscription_id VARCHAR(100) NOT NULL,
  order_reference VARCHAR(32) NOT NULL,
  invoice_payload JSON NOT NULL,
  status VARCHAR(20) NOT NULL DEFAULT 'pending',
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
  processed_at TIMESTAMPTZ
);
CREATE INDEX IF NOT EXISTS idx_mkt_deferred_invoices_status ON mkt_deferred_stripe_invoices(status);
CREATE INDEX IF NOT EXISTS idx_mkt_deferred_invoices_order ON mkt_deferred_stripe_invoices(order_reference);
