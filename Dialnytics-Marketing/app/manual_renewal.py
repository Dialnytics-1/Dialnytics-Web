"""Admin-verified bank/crypto subscription renewal.

This function is a service boundary, not a public HTTP endpoint. The caller must
verify payment outside this module and authenticate/authorize the admin. Call in
one DB transaction and commit only after all three writes succeed.
"""
from datetime import datetime, timezone
from sqlalchemy import select
from .database import Submission, ProvisioningJob, Note
from .renewal_ledger import apply_verified_renewal, RenewalError
from .renewal_sync import queue_verified_receipt
from .renewal_addon_entitlements import queue_addon_renewal

class ManualRenewalError(ValueError):
    pass


def approve_manual_renewal(db, *, order_reference: str, payment_reference: str,
                           payment_method: str, actor: str, verified: bool,
                           confirmed_at: datetime):
    """Return (paid_through, created). A repeated payment reference is idempotent.

    The reference must be the bank transaction ID or crypto tx hash, not an
    arbitrary client-generated ID. The admin is responsible for validating it.
    """
    if verified is not True:
        raise ManualRenewalError('Payment must be independently verified')
    if payment_method not in ('bank', 'crypto'):
        raise ManualRenewalError('Unsupported payment method')
    if not isinstance(actor, str) or not actor.strip():
        raise ManualRenewalError('Authenticated admin required')
    if not isinstance(confirmed_at, datetime) or confirmed_at.tzinfo is None:
        raise ManualRenewalError('Timezone-aware confirmation required')
    if not isinstance(payment_reference, str) or not 6 <= len(payment_reference.strip()) <= 180:
        raise ManualRenewalError('Valid transaction reference required')
    if not isinstance(order_reference, str) or not order_reference.strip():
        raise ManualRenewalError('Order reference required')

    order = db.scalar(select(Submission).where(
        Submission.reference == order_reference, Submission.kind == 'order'))
    job = db.get(ProvisioningJob, order_reference)
    if not order or order.status != 'paid' or not job or job.status != 'completed' or not job.dialer_account_id:
        raise ManualRenewalError('Order is not paid and provisioned')

    # A unique payment reference prevents accidental double renewals. Scope to
    # the payment method, but NOT to account/order: reuse across accounts fails.
    payment_id = f'manual:{payment_method}:{payment_reference.strip()}'
    paid_through, created = apply_verified_renewal(
        db, account_id=job.dialer_account_id, payment_id=payment_id,
        confirmed_at=confirmed_at.astimezone(timezone.utc), verified=True)
    if created:
        queue_verified_receipt(db, account_id=job.dialer_account_id,
                               payment_id=payment_id, at=confirmed_at)
        queue_addon_renewal(db, order_reference=order_reference, payment_id=payment_id)
        db.add(Note(submission_id=order.id, author=actor,
                    body=f'{payment_method} renewal verified; synchronization queued.'))
    return paid_through, created
