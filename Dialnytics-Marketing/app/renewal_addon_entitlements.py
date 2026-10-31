"""Queue paid CRM/Power Dialer extensions from verified renewal receipts.

Only call after renewal_ledger.apply_verified_renewal has committed its verified
receipt. The dialer endpoint uses the generated stable idempotency reference.
"""
import hashlib
from datetime import timezone
from sqlalchemy import select
from .database import Submission, ProvisioningJob, AddonEntitlementJob
from .renewal_ledger import RenewalReceipt
from .addon_entitlement_sync import purchased_campaigns, EntitlementSyncError


def queue_addon_renewal(db, *, order_reference: str, payment_id: str) -> bool:
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise ValueError('Payment reference required')
    receipt = db.get(RenewalReceipt, payment_id)
    if receipt is None:
        raise ValueError('Verified renewal receipt not found')
    order = db.scalar(select(Submission).where(
        Submission.reference == order_reference, Submission.kind == 'order'))
    provision = db.get(ProvisioningJob, order_reference)
    if not order or order.status != 'paid' or not provision or provision.status != 'completed':
        raise EntitlementSyncError('Order has not been paid and provisioned')
    if not provision.dialer_account_id or receipt.account_id != provision.dialer_account_id:
        raise EntitlementSyncError('Renewal account mismatch')
    if not purchased_campaigns(order):
        return False
    # Unique per payment, not per original order: the dialer API deduplicates
    # by reference, so reusing the original order reference would lose renewals.
    key = 'renewal_' + hashlib.sha256(payment_id.encode()).hexdigest()[:24]
    existing = db.get(AddonEntitlementJob, key)
    if existing:
        if existing.account_id != receipt.account_id or existing.paid_through != receipt.paid_through.date():
            raise EntitlementSyncError('Conflicting renewal entitlement')
        return False
    db.add(AddonEntitlementJob(order_reference=key, account_id=receipt.account_id,
                               paid_through=receipt.paid_through.astimezone(timezone.utc).date()))
    return True
