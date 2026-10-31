"""Idempotent, verified renewal accounting. Does not itself enable dialer access.

Call only after Stripe signature + payment status verification, or authenticated
admin approval of a reconciled bank/crypto payment. A separate entitlement
synchronizer must apply the resulting paid-through date to the dialer.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import String, DateTime, Integer, UniqueConstraint, select
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base

class RenewalError(ValueError):
    pass

class SubscriptionTerm(Base):
    __tablename__ = 'mkt_subscription_terms'
    account_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    paid_through: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    last_payment_id: Mapped[str] = mapped_column(String(200), nullable=False)
    renewal_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)

class RenewalReceipt(Base):
    __tablename__ = 'mkt_renewal_receipts'
    payment_id: Mapped[str] = mapped_column(String(200), primary_key=True)
    account_id: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    paid_through: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    confirmed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


def apply_verified_renewal(db, *, account_id, payment_id, confirmed_at, verified=False):
    """Extend by 30 days, never shorten a current subscription.

    Run inside a database transaction. On PostgreSQL, lock the subscription row
    to serialize renewals. Caller must ensure account exists and owns payment.
    """
    if verified is not True:
        raise RenewalError('Unverified payment cannot extend a subscription')
    if not isinstance(account_id, str) or not account_id.strip():
        raise RenewalError('Account ID required')
    if not isinstance(payment_id, str) or not payment_id.strip():
        raise RenewalError('Payment ID required')
    if not isinstance(confirmed_at, datetime) or confirmed_at.tzinfo is None:
        raise RenewalError('Timezone-aware confirmation time required')
    existing = db.get(RenewalReceipt, payment_id)
    if existing is not None:
        if existing.account_id != account_id:
            raise RenewalError('Payment already belongs to a different account')
        return existing.paid_through, False
    term = db.scalar(select(SubscriptionTerm).where(SubscriptionTerm.account_id == account_id).with_for_update())
    at = confirmed_at.astimezone(timezone.utc)
    previous = term.paid_through if term else at
    if previous.tzinfo is None:  # SQLite drops tzinfo; stored values are UTC.
        previous = previous.replace(tzinfo=timezone.utc)
    paid_through = max(previous, at) + timedelta(days=30)
    if term is None:
        db.add(SubscriptionTerm(account_id=account_id, paid_through=paid_through,
                                last_payment_id=payment_id, renewal_count=1))
    else:
        term.paid_through = paid_through
        term.last_payment_id = payment_id
        term.renewal_count += 1
    db.add(RenewalReceipt(payment_id=payment_id, account_id=account_id,
                          paid_through=paid_through, confirmed_at=at))
    db.flush()
    return paid_through, True
