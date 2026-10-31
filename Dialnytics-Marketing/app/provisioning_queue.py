"""Durable, idempotent dialer provisioning outbox.

This module NEVER activates a dialer user on its own. A separately authenticated
worker must consume pending jobs and confirm the dialer account/seat assignments.
Only paid orders may enqueue activation; manual payments require verified admin
approval recorded as status='paid'. The worker must use the job ID as its
idempotency key when calling the dialer backend.
"""
from datetime import timedelta
from sqlalchemy import select, update
from .database import ProvisioningJob, Submission
from .security import now

class ProvisioningError(ValueError):
    pass

def enqueue_paid_order(db, order_reference):
    if not order_reference:
        raise ProvisioningError('Missing order reference')
    order = db.scalar(select(Submission).where(
        Submission.reference == order_reference,
        Submission.kind == 'order',
        Submission.status == 'paid',
    ))
    if order is None:
        raise ProvisioningError('Order is not verified paid')
    existing = db.scalar(select(ProvisioningJob).where(
        ProvisioningJob.order_reference == order_reference))
    if existing:
        return existing
    job = ProvisioningJob(order_reference=order_reference, status='pending',
                          attempts=0, next_attempt=now())
    db.add(job)
    db.flush()
    return job

def claim_job(db, reference, *, at=None):
    at = at or now()
    result = db.execute(update(ProvisioningJob).where(
        ProvisioningJob.order_reference == reference,
        ProvisioningJob.status.in_(['pending', 'retry']),
        ProvisioningJob.next_attempt <= at,
    ).values(status='processing', attempts=ProvisioningJob.attempts + 1,
             lease_until=at + timedelta(minutes=5)))
    return result.rowcount == 1

def complete_job(db, reference, dialer_account_id):
    if not dialer_account_id or len(dialer_account_id) > 100:
        raise ProvisioningError('Valid dialer account ID required')
    result = db.execute(update(ProvisioningJob).where(
        ProvisioningJob.order_reference == reference,
        ProvisioningJob.status == 'processing',
    ).values(status='completed', dialer_account_id=dialer_account_id,
             lease_until=None, completed_at=now(), last_error=''))
    return result.rowcount == 1

def retry_job(db, reference, *, error='Provisioning failed', at=None):
    at = at or now()
    job = db.scalar(select(ProvisioningJob).where(
        ProvisioningJob.order_reference == reference,
        ProvisioningJob.status == 'processing'))
    if not job:
        return False
    delay = min(3600, 30 * (2 ** min(job.attempts, 7)))
    job.status = 'retry'
    job.lease_until = None
    job.next_attempt = at + timedelta(seconds=delay)
    job.last_error = str(error)[:200]
    return True

def recover_stale_leases(db, *, at=None):
    at = at or now()
    result = db.execute(update(ProvisioningJob).where(
        ProvisioningJob.status == 'processing',
        ProvisioningJob.lease_until <= at,
    ).values(status='retry', lease_until=None, next_attempt=at))
    return result.rowcount
