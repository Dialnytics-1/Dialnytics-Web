"""One-shot worker for pending manual accounts and expiry; never run in a web request.

The marketing database is authoritative. Remote expiry is idempotent; paid accounts
are protected again on the dialer side. Run periodically from a trusted worker.
"""
from datetime import timedelta, timezone
from sqlalchemy import select
from .database import Submission, PhoneInventory, ProvisioningJob
from .credential_vault import resolve_credentials
from .provisioning_payload import build_dialer_payload
from .dialer_http_adapter import DialerHTTPAdapter
from .security import now
from .database import make_database
import os


def process_pending(session_factory, adapter, encryption_key, *, at=None, limit=25):
    at = at or now()
    if not 1 <= limit <= 100:
        raise ValueError('Invalid batch limit')
    with session_factory() as db:
        orders = list(db.scalars(select(Submission).where(Submission.kind=='order',
            Submission.status.in_(['new','expired'])).order_by(Submission.created_at).limit(limit)).all())
    results=[]
    for order in orders:
        details=order.details or {}
        if details.get('payment') not in ('bank','usdt') or not details.get('number_ids'):
            continue
        created=order.created_at
        if created.tzinfo is None: created=created.replace(tzinfo=timezone.utc)
        deadline=created+timedelta(minutes=60)
        if order.status=='expired' or at>=deadline:
            # Expiry endpoint independently protects already activated accounts.
            status=adapter.expire_pending(order.reference)
            results.append((order.reference,status))
            continue
        with session_factory() as db:
            # Recheck before remote side effects; payment may have been approved.
            fresh=db.scalar(select(Submission).where(Submission.reference==order.reference))
            if not fresh or fresh.status!='new': continue
            inventory=list(db.scalars(select(PhoneInventory).where(
                PhoneInventory.order_reference==order.reference,
                PhoneInventory.status=='reserved')).all())
            if len(inventory)!=details.get('seats'): continue
            credentials=resolve_credentials(db,encryption_key,order.reference)
            data={'order_reference':order.reference,'seats':details['seats'],
                  'country':details['country'],'numbers':[n.e164 for n in inventory],
                  'name':order.name,'email':order.email}
            payload=build_dialer_payload(data,credentials,payment_date=at.date())
        account_id=adapter.pending(payload,idempotency_key=order.reference)
        results.append((order.reference,'pending:'+account_id))
    return results


def main():
    engine,sessions=make_database(os.environ['DATABASE_URL'])
    try:
        print(process_pending(sessions,DialerHTTPAdapter.from_environment(),
                              os.environ['DIALNYTICS_SIGNUP_FERNET_KEY']))
    finally:
        engine.dispose()

if __name__=='__main__': main()
