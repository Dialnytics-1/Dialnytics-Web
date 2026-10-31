"""Server-authoritative validation for already-owned number selection."""
from sqlalchemy import select
from .database import PhoneInventory

PROVIDERS = {'US':'telnyx','CA':'telnyx','GB':'twilio'}


def validate_number_choice(country, number_ids, seats):
    if country not in PROVIDERS:
        raise ValueError('Select US, Canada, or UK numbers.')
    if type(seats) is not int or not 1 <= seats <= 100:
        raise ValueError('Invalid seat quantity.')
    if not isinstance(number_ids,list) or len(number_ids)!=seats or any(not isinstance(x,str) or not x or len(x)>36 for x in number_ids) or len(set(number_ids))!=seats:
        raise ValueError('Select exactly one unique number per user.')


def validate_inventory_ownership(db,country,number_ids):
    rows=db.scalars(select(PhoneInventory).where(PhoneInventory.id.in_(number_ids))).all()
    if len(rows)!=len(number_ids):
        raise ValueError('A selected number is no longer available.')
    for row in rows:
        if row.country!=country or row.provider!=PROVIDERS[country] or row.number_type!='local' or row.status!='available':
            raise ValueError('Number availability changed. Please refresh your selection.')
    return rows
