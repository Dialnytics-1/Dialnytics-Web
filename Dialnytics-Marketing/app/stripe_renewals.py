"""Stripe recurring invoice handler: signed webhook event is verified by caller.
Never renew for initial checkout invoice, unpaid invoices, or an unprovisioned account.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from .database import Submission, ProvisioningJob, Note, DeferredStripeInvoice
from .renewal_ledger import apply_verified_renewal
from .renewal_sync import queue_verified_receipt
from .renewal_addon_entitlements import queue_addon_renewal

class StripeRenewalError(ValueError):
    pass

def subscription_id(invoice):
    direct = invoice.get('subscription')
    if isinstance(direct, str) and direct.startswith('sub_'):
        return direct
    details = ((invoice.get('parent') or {}).get('subscription_details') or {})
    value = details.get('subscription')
    return value if isinstance(value, str) and value.startswith('sub_') else None

def process_paid_invoice(db, invoice, *, at=None):
    """Returns outcome and order reference. Caller must commit this transaction.

    Only a signed invoice.paid event should reach this function. Matching is
    against the subscription persisted by a verified checkout webhook, never
    against customer-supplied metadata or an email address.
    """
    if not isinstance(invoice, dict):
        raise StripeRenewalError('Invalid invoice payload')
    if invoice.get('status') != 'paid' or invoice.get('paid') is not True:
        return 'ignored_unpaid', None
    if invoice.get('billing_reason') not in ('subscription_cycle',):
        return 'ignored_initial_or_manual', None
    if not isinstance(invoice.get('amount_paid'), int) or invoice['amount_paid'] <= 0:
        return 'ignored_zero_amount', None
    invoice_id = invoice.get('id')
    sub = subscription_id(invoice)
    if not isinstance(invoice_id, str) or not invoice_id.startswith('in_') or not sub:
        return 'ignored_unmatched', None
    # JSON queries are supported by PostgreSQL and SQLite. Do not trust invoice
    # metadata for account lookup: use the subscription stored at initial checkout.
    rows = db.scalars(select(Submission).where(Submission.kind == 'order', Submission.status == 'paid')).all()
    matching = [row for row in rows if (row.details or {}).get('card_payment', {}).get('subscription') == sub]
    if len(matching) != 1:
        return 'ignored_unmatched', None
    order = matching[0]
    job = db.get(ProvisioningJob, order.reference)
    if not job or job.status != 'completed' or not job.dialer_account_id:
        # Persist only verified paid invoices. Stripe may deliver renewal before
        # asynchronous account provisioning finishes; acknowledging without a
        # durable record would silently lose the customer's paid renewal.
        if db.get(DeferredStripeInvoice, invoice_id) is None:
            db.add(DeferredStripeInvoice(invoice_id=invoice_id,
                subscription_id=sub, order_reference=order.reference,
                invoice_payload=invoice, status='pending'))
        return 'awaiting_provisioning', order.reference
    at = at or datetime.now(timezone.utc)
    paid_through, created = apply_verified_renewal(
        db, account_id=job.dialer_account_id, payment_id='stripe:' + invoice_id,
        confirmed_at=at, verified=True)
    if created:
        queue_verified_receipt(db, account_id=job.dialer_account_id,
                               payment_id='stripe:' + invoice_id, at=at)
        queue_addon_renewal(db, order_reference=order.reference, payment_id='stripe:' + invoice_id)
        db.add(Note(submission_id=order.id, author='Stripe',
                    body='Recurring invoice verified; dialer renewal synchronization queued.'))
    return ('queued' if created else 'duplicate'), order.reference


def reconcile_deferred_invoices(db, *, limit=50):
    """Replay signed, previously validated renewal invoices after provisioning.

    Run from a scheduled worker. Each invoice is idempotent via renewal ledger.
    Failed rows remain pending and will be retried on the next worker run.
    """
    if not 1 <= limit <= 500:
        raise ValueError('Invalid reconciliation batch size')
    rows = db.scalars(select(DeferredStripeInvoice).where(
        DeferredStripeInvoice.status == 'pending').order_by(
        DeferredStripeInvoice.created_at).limit(limit)).all()
    outcomes = []
    for row in rows:
        result, ref = process_paid_invoice(db, row.invoice_payload)
        if result in ('queued', 'duplicate'):
            row.status = 'processed'
            row.processed_at = datetime.now(timezone.utc)
        elif result != 'awaiting_provisioning':
            row.status = 'review'
        outcomes.append((row.invoice_id, result))
    return outcomes
