"""Stripe Checkout for card payments (monthly subscription + one-time SMS registration).

Switched off unless STRIPE_SECRET_KEY and STRIPE_WEBHOOK_SECRET are set on the server.
Secret keys stay on the server; the browser is only ever given the Checkout URL Stripe returns.
Amounts always come from the server-side quote, never from the browser.
"""
import hashlib, hmac, json, logging, time, urllib.error, urllib.parse, urllib.request
from decimal import Decimal

log = logging.getLogger('dialnytics.payments')
STRIPE_API = 'https://api.stripe.com/v1'


def _cents(value) -> int:
    return int((Decimal(str(value)) * 100).quantize(Decimal('1')))


def checkout_params(quote: dict, reference: str, email: str, base_url: str, plan_slug: str, expires_at: int | None = None) -> list[tuple[str, str]]:
    """Form fields for POST /v1/checkout/sessions built from a server quote."""
    users = quote['users']
    items = [(f"Dialnytics {quote['plan_name']} plan ({users} user{'s' if users != 1 else ''})", quote['plan_total'], True)]
    items += [(f"{a['name']} add-on ({users} user{'s' if users != 1 else ''})", a['total'], True) for a in quote.get('addons', [])]
    if Decimal(quote.get('sms_setup_total') or '0') > 0:
        items.append(('SMS A2P 10DLC registration (one-time)', quote['sms_setup_total'], False))
    if Decimal(quote.get('sms_pack_total') or '0') > 0:
        items.append((f"SMS 100 pack x{quote.get('sms_packs', 1)} ({quote.get('sms_messages', 100)} messages, one-time)", quote['sms_pack_total'], False))
    if Decimal(quote.get('toll_free_total') or '0') > 0:
        n = quote.get('toll_free_count', 1)
        items.append((f"Toll-free number x{n} (one-time)", quote['toll_free_total'], False))
    p: list[tuple[str, str]] = [
        ('mode', 'subscription'),
        ('client_reference_id', reference),
        ('customer_email', email),
        ('success_url', f"{base_url}/order/thanks/?ref={urllib.parse.quote(reference)}"),
        ('cancel_url', f"{base_url}/get-started/{plan_slug}/?cancelled=1"),
        ('metadata[reference]', reference),
        ('subscription_data[metadata][reference]', reference),
        ('allow_promotion_codes', 'false'),
    ]
    if expires_at: p.append(('expires_at', str(int(expires_at))))   # Stripe minimum is 30 min after creation; the number hold is shorter and the site expires the session itself
    for i, (name, amount, recurring) in enumerate(items):
        k = f'line_items[{i}]'
        p += [(f'{k}[quantity]', '1'), (f'{k}[price_data][currency]', 'usd'),
              (f'{k}[price_data][unit_amount]', str(_cents(amount))),
              (f'{k}[price_data][product_data][name]', name),
              (f'{k}[price_data][tax_behavior]', 'inclusive')]
        if recurring:
            p.append((f'{k}[price_data][recurring][interval]', 'month'))
    return p


def create_checkout(secret_key: str, params: list[tuple[str, str]], idempotency_key: str, timeout=15) -> dict:
    req = urllib.request.Request(STRIPE_API + '/checkout/sessions', data=urllib.parse.urlencode(params).encode(), method='POST',
                                 headers={'Authorization': 'Bearer ' + secret_key, 'Idempotency-Key': idempotency_key,
                                          'Content-Type': 'application/x-www-form-urlencoded'})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return json.loads(r.read())
    except urllib.error.HTTPError as e:
        detail = e.read()[:500].decode('utf-8', 'replace')
        log.error('Stripe checkout failed (%s): %s', e.code, detail)
        raise RuntimeError('Card checkout is not available right now.')
    except (urllib.error.URLError, TimeoutError) as e:
        log.error('Stripe checkout unreachable: %s', e)
        raise RuntimeError('Card checkout is not available right now.')


def verify_webhook(payload: bytes, header: str, secret: str, tolerance=300, now=None) -> dict:
    """Check the Stripe-Signature header (HMAC-SHA256 of 't.payload'). Raises ValueError when invalid."""
    parts = {}
    for item in (header or '').split(','):
        k, _, v = item.strip().partition('=')
        parts.setdefault(k, []).append(v)
    try:
        ts = int(parts['t'][0])
    except (KeyError, ValueError):
        raise ValueError('missing timestamp')
    if abs((now or time.time()) - ts) > tolerance:
        raise ValueError('timestamp outside tolerance')
    expected = hmac.new(secret.encode(), f'{ts}.'.encode() + payload, hashlib.sha256).hexdigest()
    if not any(hmac.compare_digest(expected, sig) for sig in parts.get('v1', [])):
        raise ValueError('bad signature')
    return json.loads(payload)


def expire_checkout(secret_key: str, session_id: str, timeout=15) -> bool:
    """Close an unpaid Checkout Session so nobody can pay for a released number. False if it was already finished."""
    if not session_id: return False
    req = urllib.request.Request(f'{STRIPE_API}/checkout/sessions/{urllib.parse.quote(session_id)}/expire', data=b'', method='POST',
                                 headers={'Authorization': 'Bearer ' + secret_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: r.read(); return True
    except urllib.error.HTTPError as e:
        log.info('Stripe session %s was not expired (%s)', session_id, e.code); return False
    except (urllib.error.URLError, TimeoutError): return False


def checkout_status(secret_key: str, session_id: str, timeout=15) -> str:
    """'open' | 'complete' | 'expired' | 'unknown' (network trouble)."""
    req = urllib.request.Request(f'{STRIPE_API}/checkout/sessions/{urllib.parse.quote(session_id)}', method='GET',
                                 headers={'Authorization': 'Bearer ' + secret_key})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read()).get('status') or 'unknown'
    except urllib.error.HTTPError as e:
        return 'expired' if e.code == 404 else 'unknown'
    except (urllib.error.URLError, TimeoutError): return 'unknown'
