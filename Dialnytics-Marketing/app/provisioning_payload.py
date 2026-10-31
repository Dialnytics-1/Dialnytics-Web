"""Strict payload translation for dialer provisioning.

Credentials must be retrieved from a separate short-lived secret store; never
persist plaintext passwords in order details, logs, or a retry queue.
"""
from datetime import date, timedelta
import re

class ProvisioningPayloadError(ValueError):
    pass

def build_dialer_payload(order, credentials, *, payment_date=None):
    if not isinstance(order, dict) or not isinstance(credentials, dict):
        raise ProvisioningPayloadError('Invalid provisioning input')
    reference = order.get('order_reference')
    if not isinstance(reference, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', reference):
        raise ProvisioningPayloadError('Invalid order reference')
    seats = order.get('seats')
    numbers = order.get('numbers')
    if type(seats) is not int or not 1 <= seats <= 500 or not isinstance(numbers, list) or len(numbers) != seats:
        raise ProvisioningPayloadError('Invalid seat allocation')
    if len(set(numbers)) != seats or any(not isinstance(n, str) or not re.fullmatch(r'\+[1-9][0-9]{7,14}', n) for n in numbers):
        raise ProvisioningPayloadError('Invalid E.164 numbers')
    country = str(order.get('country', '')).upper()
    if country not in ('US', 'CA', 'UK', 'GB'):
        raise ProvisioningPayloadError('Unsupported country')
    name = credentials.get('name') or order.get('name')
    email = credentials.get('email') or order.get('email')
    password = credentials.get('password')
    if not isinstance(name, str) or not name.strip() or not isinstance(email, str) or '@' not in email or not isinstance(password, str) or len(password) < 12:
        raise ProvisioningPayloadError('Missing secure customer credentials')
    start = payment_date or date.today()
    if not isinstance(start, date):
        raise ProvisioningPayloadError('Invalid payment date')
    return {'order_reference': reference, 'name': name.strip(), 'email': email.strip().lower(),
            'password': password, 'country': country, 'numbers': numbers,
            'plan_start': start.isoformat(), 'plan_renewal': (start + timedelta(days=30)).isoformat()}
