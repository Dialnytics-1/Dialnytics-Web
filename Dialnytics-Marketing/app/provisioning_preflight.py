"""Fail-closed checks before a paid order is sent to dialer provisioning.

This does not create accounts, purchase numbers, or activate service. The
checkout must store immutable validated order details with number_ids and seats.
"""
from sqlalchemy import select
from .database import Submission, PhoneInventory

class PreflightError(ValueError):
    pass

PROVIDERS = {'US': 'telnyx', 'CA': 'telnyx', 'UK': 'twilio', 'GB': 'twilio'}

def check_paid_order(db, reference):
    order = db.scalar(select(Submission).where(
        Submission.reference == reference, Submission.kind == 'order'))
    if order is None or order.status != 'paid':
        raise PreflightError('Order must have verified paid status')
    details = order.details if isinstance(order.details, dict) else {}
    seats = details.get('seats')
    if type(seats) is not int or not 1 <= seats <= 500:
        raise PreflightError('Invalid seat count')
    country = str(details.get('country', '')).upper()
    if country not in PROVIDERS:
        raise PreflightError('Unsupported country')
    number_ids = details.get('number_ids')
    if not isinstance(number_ids, list) or len(number_ids) != seats or any(not isinstance(x, str) or not x for x in number_ids) or len(set(number_ids)) != seats:
        raise PreflightError('One unique number per seat is required')
    numbers = db.scalars(select(PhoneInventory).where(PhoneInventory.id.in_(number_ids))).all()
    if len(numbers) != seats:
        raise PreflightError('Selected number inventory incomplete')
    for number in numbers:
        if (number.status != 'reserved' or number.order_reference != reference
            or number.country.upper() not in ({'GB', 'UK'} if country in ('GB','UK') else {country})
            or number.provider.lower() != PROVIDERS[country]):
            raise PreflightError('Number is not reserved for this paid order and provider')
    return {'order_reference': reference, 'seats': seats, 'country': country,
            'number_ids': sorted(number_ids), 'numbers': [n.e164 for n in sorted(numbers, key=lambda n: n.e164)], 'email': order.email, 'name': order.name,
            'payment_date': _payment_date(order)}


def _payment_date(order):
    from datetime import date, datetime
    details = order.details or {}
    raw = (details.get('card_payment') or {}).get('paid_at')
    if isinstance(raw, str):
        try: return datetime.fromisoformat(raw.replace('Z','+00:00')).date()
        except ValueError: pass
    return (order.updated_at or order.created_at).date()
