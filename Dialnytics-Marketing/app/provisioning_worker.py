"""Provisioning orchestrator with a deliberately injected dialer adapter.

The adapter must provide idempotent provision(order, idempotency_key) and
return a durable dialer account ID. No HTTP credentials are stored here.
This is NOT a production worker until a real authenticated dialer adapter,
atomic assignment, and worker scheduler are implemented and tested.
"""
from dataclasses import dataclass
from .provisioning_preflight import check_paid_order, PreflightError
from .provisioning_queue import claim_job, complete_job, retry_job, ProvisioningError

@dataclass(frozen=True)
class ProvisioningResult:
    status: str
    order_reference: str
    account_id: str = ''


def process_order(session_factory, order_reference, dialer_adapter, credential_resolver=None, credential_cleanup=None):
    """Claim and validate a paid job, then call the injected idempotent adapter.

    The adapter must treat order_reference as a stable idempotency key.
    DB commits are deliberately separate from remote calls: a retry after
    network failure must never create duplicate dialer accounts.
    """
    if not order_reference or not isinstance(order_reference, str):
        raise ValueError('Order reference required')
    with session_factory() as db:
        if not claim_job(db, order_reference):
            return ProvisioningResult('not_claimed', order_reference)
        db.commit()
    try:
        with session_factory() as db:
            payload = check_paid_order(db, order_reference)
        if credential_resolver is not None:
            from .provisioning_payload import build_dialer_payload
            credentials = credential_resolver(order_reference)
            payload = build_dialer_payload(payload, credentials, payment_date=payload.get("payment_date"))
        account_id = dialer_adapter.provision(payload, idempotency_key=order_reference)
        if not isinstance(account_id, str) or not account_id.strip():
            raise ProvisioningError('Dialer adapter returned no account ID')
        with session_factory() as db:
            if not complete_job(db, order_reference, account_id):
                raise ProvisioningError('Provisioning lease lost')
            db.commit()
        # Delete temporary signup credentials only AFTER durable job completion.
        # Cleanup failures are recoverable and must never trigger a second account creation.
        if credential_cleanup is not None:
            try:
                credential_cleanup(order_reference)
            except Exception:
                pass  # Periodic vault expiry cleanup is the fallback.
        return ProvisioningResult('completed', order_reference, account_id)
    except Exception as exc:
        with session_factory() as db:
            retry_job(db, order_reference, error=type(exc).__name__)
            db.commit()
        return ProvisioningResult('retry', order_reference)
