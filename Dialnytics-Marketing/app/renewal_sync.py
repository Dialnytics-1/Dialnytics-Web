"""Durable renewal entitlement synchronization outbox.

A verified renewal is recorded separately in renewal_ledger. This module queues
an update for the dialer; it never treats a queued update as activated.
"""
from datetime import datetime, timedelta, timezone
from sqlalchemy import DateTime, Integer, String, select, update
from sqlalchemy.orm import Mapped, mapped_column
from .database import Base
from .renewal_ledger import RenewalReceipt, SubscriptionTerm


class RenewalSyncError(ValueError):
    pass


class RenewalSyncJob(Base):
    __tablename__ = 'mkt_renewal_sync_jobs'
    account_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    status: Mapped[str] = mapped_column(String(20), nullable=False, default='pending')
    target_paid_through: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    attempts: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    next_attempt: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    lease_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_error: Mapped[str] = mapped_column(String(200), nullable=False, default='')


def _utc(value):
    if not isinstance(value, datetime):
        raise RenewalSyncError('Invalid date')
    return value.replace(tzinfo=timezone.utc) if value.tzinfo is None else value.astimezone(timezone.utc)


def queue_verified_receipt(db, *, account_id, payment_id, at):
    """Queue latest paid-through date only for a persisted verified receipt.

    Call within the same transaction as the verified renewal ledger write.
    Concurrent writers for the same account must be serialized by the caller.
    """
    receipt = db.get(RenewalReceipt, payment_id)
    term = db.get(SubscriptionTerm, account_id)
    if receipt is None or receipt.account_id != account_id or term is None:
        raise RenewalSyncError('No verified renewal receipt for this account')
    target = _utc(term.paid_through)
    at = _utc(at)
    job = db.get(RenewalSyncJob, account_id)
    if job is None:
        job = RenewalSyncJob(account_id=account_id, status='pending',
                             target_paid_through=target, next_attempt=at)
        db.add(job)
    elif target > _utc(job.target_paid_through):
        job.target_paid_through = target
        # In-flight requests may finish for the older term; completion checks
        # the target to prevent falsely marking the newer term synced.
        job.status = 'pending'
        job.next_attempt = at
        job.lease_until = None
    db.flush()
    return job


def claim_sync(db, *, account_id, at):
    at = _utc(at)
    result = db.execute(update(RenewalSyncJob).where(
        RenewalSyncJob.account_id == account_id,
        RenewalSyncJob.status.in_(['pending', 'retry']),
        RenewalSyncJob.next_attempt <= at,
    ).values(status='processing', attempts=RenewalSyncJob.attempts + 1,
             lease_until=at + timedelta(minutes=5)))
    return result.rowcount == 1


def complete_sync(db, *, account_id, target_paid_through):
    """Only acknowledge the exact target actually applied by the dialer."""
    result = db.execute(update(RenewalSyncJob).where(
        RenewalSyncJob.account_id == account_id,
        RenewalSyncJob.status == 'processing',
        RenewalSyncJob.target_paid_through == _utc(target_paid_through),
    ).values(status='completed', lease_until=None, last_error=''))
    return result.rowcount == 1


def retry_sync(db, *, account_id, at, error):
    job = db.get(RenewalSyncJob, account_id)
    if job is None or job.status != 'processing':
        return False
    job.status = 'retry'
    job.lease_until = None
    job.next_attempt = _utc(at) + timedelta(seconds=min(3600, 30 * 2 ** min(job.attempts, 7)))
    job.last_error = str(error)[:200]
    return True


def recover_stale_syncs(db, *, at):
    result = db.execute(update(RenewalSyncJob).where(
        RenewalSyncJob.status == 'processing',
        RenewalSyncJob.lease_until <= _utc(at),
    ).values(status='retry', lease_until=None, next_attempt=_utc(at)))
    return result.rowcount
