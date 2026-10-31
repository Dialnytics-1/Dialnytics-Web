"""Fail-closed, authenticated sync of dialer-owned numbers into marketing inventory."""
import hmac
import json
import os
import time
import uuid
from urllib.request import Request, urlopen
from urllib.error import URLError
from sqlalchemy import select
from .database import PhoneInventory

_last_sync = 0.0


def fetch_owned_numbers():
    base = os.getenv('DIALER_INTERNAL_URL', '').rstrip('/')
    token = os.getenv('DIALER_INTERNAL_TOKEN', '')
    if not base.startswith('https://') or len(token) < 32:
        raise RuntimeError('Dialer inventory sync is not configured')
    req = Request(base + '/internal/owned-numbers', headers={'Authorization': 'Bearer ' + token,
                                                              'Accept': 'application/json'})
    with urlopen(req, timeout=12) as response:
        if response.status != 200:
            raise RuntimeError('Dialer inventory request failed')
        data = json.load(response)
    if not isinstance(data, dict) or not isinstance(data.get('numbers'), list) or not data.get('complete'):
        raise RuntimeError('Incomplete dialer inventory response')
    return data['numbers']


def reconcile(db, feed):
    """Never release a reservation/assignment. No deletions on a failed sync."""
    clean = {}
    for row in feed:
        if not isinstance(row, dict):
            raise ValueError('Invalid inventory record')
        num, country, provider, kind = (row.get(k) for k in ('number', 'country', 'provider', 'type'))
        import re
        if not isinstance(num, str) or not re.fullmatch(r'\+[1-9]\d{7,14}', num):
            raise ValueError('Invalid inventory number')
        if country not in ('US','CA','GB') or provider not in ('telnyx','twilio') or kind not in ('local','toll_free'):
            raise ValueError('Invalid inventory metadata')
        if (country == 'GB') != (provider == 'twilio') or num in clean:
            raise ValueError('Conflicting inventory entry')
        clean[num] = (country, provider, kind)
    existing = {r.e164:r for r in db.scalars(select(PhoneInventory).with_for_update()).all()}
    created = changed = 0
    for num, (country, provider, kind) in clean.items():
        row = existing.get(num)
        if row is None:
            db.add(PhoneInventory(id=str(uuid.uuid4()), e164=num, country=country,
                                  provider=provider, number_type=kind, status='available'))
            created += 1
        else:
            if row.status == 'assigned' or row.status == 'reserved':
                continue
            row.country, row.provider, row.number_type = country, provider, kind
            if row.status != 'available':
                row.status = 'available'
                changed += 1
    for num, row in existing.items():
        if num not in clean and row.status == 'available':
            row.status = 'unavailable'
            changed += 1
    return {'created': created, 'changed': changed, 'total': len(clean)}


def sync_inventory(DB, *, force=False):
    global _last_sync
    if not force and time.monotonic() - _last_sync < 60:
        return {'cached': True}
    feed = fetch_owned_numbers()  # fail before any DB changes
    with DB.begin() as db:
        result = reconcile(db, feed)
    _last_sync = time.monotonic()
    return result
