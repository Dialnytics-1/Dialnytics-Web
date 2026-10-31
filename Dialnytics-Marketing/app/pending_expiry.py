"""Expire unpaid manual-payment orders and release their reserved numbers.

Run via a trusted scheduled worker. Never delete paid orders or dialer accounts.
Dialer-account cleanup is intentionally deferred until a verified provisioning
link exists; deleting users by email/reference alone is unsafe.
"""
from datetime import timedelta
from sqlalchemy import select, update
from .database import Submission, PhoneInventory
from .security import now

MANUAL_METHODS = frozenset({'bank', 'usdt'})

def expire_manual_orders(db, *, at=None, minutes=60):
    at = at or now()
    cutoff = at - timedelta(minutes=minutes)
    candidates = db.scalars(select(Submission).where(
        Submission.kind == 'order',
        Submission.status == 'new',
        Submission.created_at <= cutoff,
    )).all()
    expired = []
    for order in candidates:
        if (order.details or {}).get('payment') not in MANUAL_METHODS:
            continue
        # Conditional update prevents overriding concurrent admin approval.
        changed = db.execute(update(Submission).where(
            Submission.id == order.id,
            Submission.status == 'new',
        ).values(status='expired', updated_at=at))
        if changed.rowcount != 1:
            continue
        db.execute(update(PhoneInventory).where(
            PhoneInventory.order_reference == order.reference,
            PhoneInventory.status == 'reserved',
        ).values(status='available', order_reference='', reserved_until=None))
        expired.append(order.reference)
    return expired
