"""Manual-payment approval: only an authenticated admin may call this service.

No customer-facing endpoint may mark orders paid. The transaction atomically
claims an eligible order and enqueues provisioning. Expired orders cannot be
resurrected; late payments require manual reconciliation.
"""
from datetime import timedelta
from sqlalchemy import update, select
from .database import Submission, PhoneInventory, Note
from .provisioning_queue import enqueue_paid_order
from .security import now

class ApprovalError(ValueError):
    pass

def approve_manual_order(db, reference, *, actor, at=None):
    at = at or now()
    order = db.scalar(select(Submission).where(Submission.reference == reference, Submission.kind == 'order'))
    if order is None:
        raise ApprovalError('Order not found')
    if (order.details or {}).get('payment') not in ('bank', 'usdt'):
        raise ApprovalError('Not a manual-payment order')
    if order.status == 'paid':
        return 'already_paid'
    if order.status != 'new':
        raise ApprovalError('Order is not pending')
    created = order.created_at
    if created.tzinfo is None:
        from datetime import timezone
        created = created.replace(tzinfo=timezone.utc)
    if at >= created + timedelta(minutes=60):
        raise ApprovalError('Payment window expired; reconcile manually')
    ids = (order.details or {}).get('number_ids') or []
    if ids:
        numbers = db.scalars(select(PhoneInventory).where(PhoneInventory.id.in_(ids))).all()
        if len(numbers) != len(ids) or any(n.status != 'reserved' or n.order_reference != reference for n in numbers):
            raise ApprovalError('Selected number reservation is no longer valid')
    changed = db.execute(update(Submission).where(Submission.id == order.id, Submission.status == 'new')
        .values(status='paid', updated_at=at))
    if changed.rowcount != 1:
        raise ApprovalError('Order changed concurrently')
    db.flush()
    enqueue_paid_order(db, reference)
    db.add(Note(submission_id=order.id, body='Manual payment confirmed by admin; provisioning queued.', author=actor))
    return 'approved'
