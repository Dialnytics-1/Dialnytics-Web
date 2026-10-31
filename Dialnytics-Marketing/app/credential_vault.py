"""Encrypted, time-limited signup credentials for provisioning.

Development component: callers must create the database table via migration,
secure the encryption key outside the database, and never log plaintext secrets.
"""
from datetime import datetime, timedelta, timezone
import json
import re
from cryptography.fernet import Fernet, InvalidToken
from sqlalchemy import Column, DateTime, LargeBinary, String, select
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class SignupSecret(Base):
    __tablename__ = 'mkt_signup_secrets'
    order_reference = Column(String(128), primary_key=True)
    encrypted_payload = Column(LargeBinary, nullable=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)

class CredentialVaultError(ValueError):
    pass


def _cipher(key):
    try:
        return Fernet(key)
    except (ValueError, TypeError) as exc:
        raise CredentialVaultError('Invalid credential encryption key') from exc


def store_credentials(db, key, order_reference, credentials, *, now=None, ttl_minutes=120):
    if not isinstance(order_reference, str) or not re.fullmatch(r'[A-Za-z0-9_-]{8,128}', order_reference):
        raise CredentialVaultError('Invalid order reference')
    if not isinstance(credentials, dict) or not isinstance(credentials.get('password'), str) or len(credentials['password']) < 12:
        raise CredentialVaultError('Invalid signup credentials')
    if not 1 <= ttl_minutes <= 1440:
        raise CredentialVaultError('Invalid TTL')
    now = now or datetime.now(timezone.utc)
    payload = json.dumps(credentials, separators=(',', ':')).encode('utf-8')
    record = db.get(SignupSecret, order_reference)
    if record is not None:
        raise CredentialVaultError('Credentials already stored for order')
    db.add(SignupSecret(order_reference=order_reference, encrypted_payload=_cipher(key).encrypt(payload),
                        expires_at=now + timedelta(minutes=ttl_minutes)))


def resolve_credentials(db, key, order_reference, *, now=None):
    record = db.get(SignupSecret, order_reference)
    if record is None:
        raise CredentialVaultError('Credentials unavailable')
    now = now or datetime.now(timezone.utc)
    expiry = record.expires_at
    if expiry.tzinfo is None:
        expiry = expiry.replace(tzinfo=timezone.utc)
    if now >= expiry:
        raise CredentialVaultError('Credentials expired; customer must re-enter password securely')
    try:
        return json.loads(_cipher(key).decrypt(record.encrypted_payload).decode('utf-8'))
    except (InvalidToken, UnicodeDecodeError, ValueError) as exc:
        raise CredentialVaultError('Cannot decrypt signup credentials') from exc


def delete_credentials(db, order_reference):
    record = db.get(SignupSecret, order_reference)
    if record is not None:
        db.delete(record)
        return True
    return False


def purge_expired(db, *, now=None):
    now = now or datetime.now(timezone.utc)
    records = db.scalars(select(SignupSecret)).all()
    count = 0
    for record in records:
        expiry = record.expires_at
        if expiry.tzinfo is None:
            expiry = expiry.replace(tzinfo=timezone.utc)
        if expiry <= now:
            db.delete(record)
            count += 1
    return count
