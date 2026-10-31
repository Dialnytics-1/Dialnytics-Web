"""Durable, payment-gated account-wide add-on sync after provisioning.

Never trust checkout flags alone. Only a completed paid provisioning job is eligible.
"""
import json
import urllib.request
import urllib.parse
from datetime import timedelta, date
from sqlalchemy import select, update
from .database import Submission, ProvisioningJob, AddonEntitlementJob
from .security import now

class EntitlementSyncError(RuntimeError): pass

def purchased_campaigns(order):
    details = order.details if isinstance(order.details, dict) else {}
    addons = details.get('addons') or []
    return any((item.get('key') == 'campaigns') for item in addons if isinstance(item, dict))

def enqueue_for_paid_order(db, reference):
    order = db.scalar(select(Submission).where(Submission.reference == reference, Submission.kind == 'order'))
    provision = db.get(ProvisioningJob, reference)
    if not order or order.status != 'paid' or not provision or provision.status != 'completed' or not provision.dialer_account_id:
        return False
    if not purchased_campaigns(order):
        return False
    existing = db.get(AddonEntitlementJob, reference)
    if existing:
        if existing.account_id != provision.dialer_account_id:
            raise EntitlementSyncError('Order account mismatch')
        return False
    details = order.details or {}
    raw = (details.get('card_payment') or {}).get('paid_at')
    from datetime import datetime
    try:
        start = datetime.fromisoformat(raw.replace('Z','+00:00')).date() if raw else order.updated_at.date()
    except (ValueError, AttributeError):
        start = order.updated_at.date()
    db.add(AddonEntitlementJob(order_reference=reference, account_id=provision.dialer_account_id,
                               paid_through=start + timedelta(days=30)))
    return True

class EntitlementHTTPAdapter:
    def __init__(self, base_url, token, opener=None):
        url = urllib.parse.urlsplit(base_url)
        if url.scheme != 'https' or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError('HTTPS backend URL required')
        if not isinstance(token, str) or len(token) < 32:
            raise ValueError('Strong internal token required')
        self.url = base_url.rstrip('/') + '/api/internal/crm-power-entitlement'
        self.token = token
        self.opener = opener or urllib.request.urlopen

    def sync(self, job):
        payload = {'account_id': job.account_id, 'order_reference': job.order_reference,
                   'enabled': True, 'paid_through': job.paid_through.isoformat()}
        request = urllib.request.Request(self.url, data=json.dumps(payload).encode(), method='POST', headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with self.opener(request, timeout=12) as response:
                if response.status != 200: raise EntitlementSyncError('Rejected')
                result = json.loads(response.read(4096))
        except Exception as exc:
            raise EntitlementSyncError('Entitlement synchronization failed') from exc
        if result.get('status') not in ('applied', 'already_applied') or result.get('account_id') != job.account_id:
            raise EntitlementSyncError('Invalid acknowledgement')
        return result

def process_pending(session_factory, adapter, *, limit=25):
    if type(limit) is not int or not 1 <= limit <= 100: raise ValueError('Invalid limit')
    with session_factory.begin() as db:
        # Recover crashed workers; remote endpoint is idempotent by order_reference.
        db.execute(update(AddonEntitlementJob).where(
            AddonEntitlementJob.status == 'processing',
            AddonEntitlementJob.next_attempt <= now()
        ).values(status='retry'))
    with session_factory() as db:
        references = list(db.scalars(select(AddonEntitlementJob.order_reference).where(
            AddonEntitlementJob.status.in_(['pending','retry']),
            AddonEntitlementJob.next_attempt <= now()).order_by(AddonEntitlementJob.next_attempt).limit(limit)).all())
    results=[]
    for reference in references:
        with session_factory.begin() as db:
            job = db.get(AddonEntitlementJob, reference)
            if not job or job.status not in ('pending','retry') or job.next_attempt > now(): continue
            job.status='processing'
            job.next_attempt=now()+timedelta(minutes=3)
            job.attempts += 1
            snapshot = (job.order_reference, job.account_id, job.paid_through)
        from types import SimpleNamespace
        try:
            adapter.sync(SimpleNamespace(order_reference=snapshot[0], account_id=snapshot[1], paid_through=snapshot[2]))
            state='completed'
        except Exception:
            state='retry'
        with session_factory.begin() as db:
            job = db.get(AddonEntitlementJob, reference)
            if job and job.status=='processing':
                job.status=state
                if state=='retry': job.next_attempt=now()+timedelta(minutes=min(60, 2 ** min(job.attempts, 6)))
                else: job.completed_at=now()
        results.append((reference,state))
    return results
