import hashlib, secrets, hmac
from datetime import datetime, timezone
from itsdangerous import URLSafeTimedSerializer, BadSignature

def now(): return datetime.now(timezone.utc)

def hash_password(password: str) -> str:
    if len(password) < 12: raise ValueError('Use at least 12 characters for the admin password.')
    salt=secrets.token_bytes(16)
    digest=hashlib.scrypt(password.encode(),salt=salt,n=16384,r=8,p=1,dklen=32)
    return 'scrypt$'+salt.hex()+'$'+digest.hex()

def verify_password(password: str, encoded: str) -> bool:
    try:
        kind,salt,digest=encoded.split('$')
        if kind!='scrypt' or len(password)>1024: return False
        actual=hashlib.scrypt(password.encode(),salt=bytes.fromhex(salt),n=16384,r=8,p=1,dklen=32)
        return hmac.compare_digest(actual,bytes.fromhex(digest))
    except (ValueError,TypeError): return False

def sha(value): return hashlib.sha256(value.encode()).hexdigest()

def form_token(secret, audience): return URLSafeTimedSerializer(secret,salt='mkt-form-v1').dumps({'aud':audience,'nonce':secrets.token_hex(16)})

def valid_form_token(secret, token, audience):
    try: return URLSafeTimedSerializer(secret,salt='mkt-form-v1').loads(token,max_age=7200).get('aud')==audience
    except (BadSignature,TypeError,AttributeError): return False

def csv_safe(value):
    text=str(value or '')
    return "'"+text if text.lstrip().startswith(('=','+','-','@','\t','\r')) else text
