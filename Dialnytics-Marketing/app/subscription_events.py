"""Resolve subscription lifecycle webhooks without trusting customer metadata.

The caller must first verify the Stripe webhook signature.  A cancellation
stops future renewals; it does not revoke already paid dialer access.
"""
from sqlalchemy import select
from .database import Submission, Note

EVENTS = {'customer.subscription.deleted': 'cancelled',
          'invoice.payment_failed': 'payment_failed'}


def subscription_from_event(kind, obj):
    if not isinstance(obj, dict):
        return None
    if kind == 'customer.subscription.deleted':
        value = obj.get('id')
    elif kind == 'invoice.payment_failed':
        value = obj.get('subscription')
        if not value:
            value = ((obj.get('parent') or {}).get('subscription_details') or {}).get('subscription')
    else:
        return None
    return value if isinstance(value, str) and value.startswith('sub_') else None


def apply_subscription_event(db, kind, obj, *, timestamp):
    """Update one matching paid order; ambiguous matches are ignored safely."""
    if kind not in EVENTS:
        return 'ignored_event'
    sub = subscription_from_event(kind, obj)
    if not sub:
        return 'ignored_no_subscription'
    rows = db.scalars(select(Submission).where(
        Submission.kind == 'order', Submission.status == 'paid')).all()
    matching = [row for row in rows if
                (row.details or {}).get('card_payment', {}).get('subscription') == sub]
    if len(matching) != 1:
        return 'ignored_unmatched'
    row = matching[0]
    details = dict(row.details or {})
    card = dict(details.get('card_payment') or {})
    status = EVENTS[kind]
    marker = 'cancelled_at' if status == 'cancelled' else 'failed_at'
    # Do not overwrite a confirmed cancellation with a later failed invoice.
    if card.get('status') == 'cancelled' and status == 'payment_failed':
        return 'ignored_cancelled'
    if card.get('status') == status and card.get(marker):
        return 'duplicate'
    card.update(status=status, **{marker: timestamp.isoformat()})
    details['card_payment'] = card
    row.details = details
    row.updated_at = timestamp
    db.add(Note(submission_id=row.id, author='Stripe',
                body='Stripe subscription cancelled; paid access retained until expiry.'
                if status == 'cancelled' else 'Stripe renewal payment failed; payment review required.'))
    return 'updated'
