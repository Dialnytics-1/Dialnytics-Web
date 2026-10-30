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


def checkout_params(quote: dict, reference: str, email: str, base_url: str, plan_slug: str) -> list[tuple[str, str]]:
    """Form fields for POST /v1/checkout/sessions built from a server quote."""
    users = quote['users']
    items = [(f"Dialnytics {quote['plan_name']} plan ({users} user{'s' if users != 1 else ''})", quote['plan_total'], True)]
    items += [(f"{a['name']} add-on ({users} user{'s' if users != 1 else ''})", a['total'], True) for a in quote.get('addons', [])]
    if Decimal(quote.get('one_time_total') or '0') > 0:
        items.append(('SMS A2P 10DLC registration (one-time)', quote['one_time_total'], False))
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
