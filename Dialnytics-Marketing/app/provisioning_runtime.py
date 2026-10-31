"""Explicit, one-shot operational worker. Not started by web requests.

Requires separately configured Render Cron Job / worker with same marketing DB.
"""
import os
from sqlalchemy import select
from .database import make_database, ProvisioningJob
from .provisioning_queue import recover_stale_leases
from .provisioning_worker import process_order
from .dialer_http_adapter import DialerHTTPAdapter
from .credential_vault import resolve_credentials, delete_credentials
from .pending_expiry import expire_manual_orders
from .number_reservations import release_expired, assign_numbers
from .security import now


def process_batch(session_factory, adapter, key, *, limit=20):
    if not 1 <= limit <= 100: raise ValueError('Invalid batch size')
    with session_factory.begin() as db:
        recover_stale_leases(db)
        expire_manual_orders(db)
        # Do not purge paid-order credentials before provisioning; expired secrets
        # require customer re-entry and an explicit recovery workflow.
        release_expired(db)
    with session_factory() as db:
        references=list(db.scalars(select(ProvisioningJob.order_reference).where(
            ProvisioningJob.status.in_(['pending','retry']),
            ProvisioningJob.next_attempt <= now(),
        ).order_by(ProvisioningJob.next_attempt).limit(limit)).all())
    results=[]
    for reference in references:
        def credentials(ref):
            with session_factory() as db:
                return resolve_credentials(db,key,ref)
        def cleanup(ref):
            with session_factory.begin() as db:
                delete_credentials(db,ref)
        result=process_order(session_factory,reference,adapter,
                             credential_resolver=credentials,credential_cleanup=cleanup)
        if result.status=='completed':
            # Only mark inventory assigned AFTER the dialer acknowledged provisioning.
            # If this local update fails, the completed job remains visible for admin repair.
            from .database import PhoneInventory
            with session_factory.begin() as db:
                ids=list(db.scalars(select(PhoneInventory.id).where(
                    PhoneInventory.order_reference==reference,
                    PhoneInventory.status=='reserved')).all())
                if ids: assign_numbers(db,reference,ids)
        if result.status=='completed':
            from .addon_entitlement_sync import enqueue_for_paid_order
            with session_factory.begin() as db:
                enqueue_for_paid_order(db, reference)
        results.append(result)
    # Reconcile verified Stripe renewal invoices that arrived before provisioning.
    from .stripe_renewals import reconcile_deferred_invoices
    with session_factory.begin() as db:
        reconcile_deferred_invoices(db)
    return results


def main():
    url=os.environ['DATABASE_URL']
    key=os.environ['DIALNYTICS_SIGNUP_FERNET_KEY']
    adapter=DialerHTTPAdapter.from_environment()
    engine,sessions=make_database(url)
    try:
        results=process_batch(sessions,adapter,key)
        print('Provisioning jobs processed:',len(results))
        for result in results:
            print(result.order_reference, result.status)
    finally:
        engine.dispose()

if __name__=='__main__':
    main()
