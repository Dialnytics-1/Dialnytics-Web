"""One-shot renewal synchronization consumer for a separately scheduled worker.

No customer-controlled callback may enqueue jobs: the renewal ledger must first
record a verified payment. Never run from a web request or on module import.
"""
import os
from datetime import datetime, timezone
from sqlalchemy import select
from .database import make_database
from .renewal_sync import (RenewalSyncJob, claim_sync, complete_sync,
                           recover_stale_syncs, retry_sync)
from .renewal_http_adapter import RenewalHTTPAdapter


def process_renewals(session_factory, adapter, *, limit=25, clock=None):
    if not isinstance(limit, int) or not 1 <= limit <= 100:
        raise ValueError('limit must be between 1 and 100')
    clock = clock or (lambda: datetime.now(timezone.utc))
    with session_factory.begin() as db:
        recover_stale_syncs(db, at=clock())
    with session_factory() as db:
        account_ids = list(db.scalars(select(RenewalSyncJob.account_id).where(
            RenewalSyncJob.status.in_(['pending', 'retry']),
            RenewalSyncJob.next_attempt <= clock(),
        ).order_by(RenewalSyncJob.next_attempt).limit(limit)).all())
    outcomes = []
    for account_id in account_ids:
        with session_factory.begin() as db:
            if not claim_sync(db, account_id=account_id, at=clock()):
                outcomes.append((account_id, 'skipped'))
                continue
            job = db.get(RenewalSyncJob, account_id)
            target = job.target_paid_through
        try:
            adapter.sync(account_id, target)
        except Exception as exc:
            # Avoid storing raw transport errors containing potential secrets.
            with session_factory.begin() as db:
                retry_sync(db, account_id=account_id, at=clock(), error=type(exc).__name__)
            outcomes.append((account_id, 'retry'))
            continue
        with session_factory.begin() as db:
            acknowledged = complete_sync(db, account_id=account_id, target_paid_through=target)
        outcomes.append((account_id, 'completed' if acknowledged else 'superseded'))
    return outcomes


def main():
    token = os.environ['DIALER_INTERNAL_API_TOKEN']
    base_url = os.environ['DIALER_BACKEND_URL']
    adapter = RenewalHTTPAdapter(base_url, token)
    engine, sessions = make_database(os.environ['DATABASE_URL'])
    try:
        for account_id, status in process_renewals(sessions, adapter):
            print('renewal', account_id, status)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
