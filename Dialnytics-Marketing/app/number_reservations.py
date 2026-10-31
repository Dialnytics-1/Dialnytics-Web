"""Atomic reservations of pre-owned phone numbers for a marketing checkout.

The caller must verify payment before calling assign_numbers. No provider purchase
is performed here. Use a transactional DB session; never expose this module to
unauthenticated requests directly.
"""
from datetime import timedelta
from sqlalchemy import select, update
from .database import PhoneInventory, Submission
from .security import now


class InventoryConflict(ValueError):
    pass


def reserve_numbers(db, order_reference: str, number_ids: list[str], *, minutes: int = 60):
    """Reserve exact numbers for one order; all-or-nothing, safe under concurrency."""
    if not order_reference or not number_ids or len(set(number_ids)) != len(number_ids):
        raise InventoryConflict('Invalid order or duplicate number selection')
    if not 1 <= minutes <= 60:
        raise InventoryConflict('Invalid reservation duration')
    expires = now() + timedelta(minutes=minutes)
    for number_id in sorted(number_ids):
        result = db.execute(
            update(PhoneInventory).where(
                PhoneInventory.id == number_id,
                PhoneInventory.status == 'available',
            ).values(status='reserved', order_reference=order_reference,
                     reserved_until=expires)
        )
        if result.rowcount != 1:
            raise InventoryConflict('A selected number is no longer available')
    return expires


def release_expired(db, *, at=None):
    """Release expired holds ONLY for orders not verified as paid.

    A paid checkout can be awaiting an asynchronous provisioning worker. Releasing
    its number would allow another buyer to reserve it after 60 minutes.
    Orphan holds are released, but paid orders remain reserved for recovery.
    """
    at = at or now()
    expired = list(db.scalars(select(PhoneInventory).where(
        PhoneInventory.status == 'reserved',
        PhoneInventory.reserved_until <= at,
    )).all())
    released = 0
    for number in expired:
        order = db.scalar(select(Submission).where(
            Submission.reference == number.order_reference,
            Submission.kind == 'order',
        ))
        if order is not None and order.status == 'paid':
            continue
        result = db.execute(update(PhoneInventory).where(
            PhoneInventory.id == number.id,
            PhoneInventory.status == 'reserved',
            PhoneInventory.order_reference == number.order_reference,
            PhoneInventory.reserved_until <= at,
        ).values(status='available', order_reference='', reserved_until=None).execution_options(synchronize_session=False))
        released += result.rowcount
    return released


def assign_numbers(db, order_reference: str, number_ids: list[str]):
    """Mark already-reserved numbers assigned after verified payment.

    The caller is responsible for checking the order's payment state and for
    provisioning the matching dialer seats before declaring calling active.
    """
    if not order_reference or not number_ids or len(set(number_ids)) != len(number_ids):
        raise InventoryConflict('Invalid assignment')
    for number_id in sorted(number_ids):
        result = db.execute(
            update(PhoneInventory).where(
                PhoneInventory.id == number_id,
                PhoneInventory.status == 'reserved',
                PhoneInventory.order_reference == order_reference,
            ).values(status='assigned', reserved_until=None)
        )
        if result.rowcount != 1:
            raise InventoryConflict('Number is not reserved for this order')


def list_available(db, country: str, number_type: str = 'local'):
    return db.scalars(select(PhoneInventory).where(
        PhoneInventory.country == country,
        PhoneInventory.number_type == number_type,
        PhoneInventory.status == 'available',
    ).order_by(PhoneInventory.e164)).all()
