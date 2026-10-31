"""Authenticated HTTPS transport for provisioning (development integration).

The dialer must independently implement the matching internal endpoint and
idempotency storage. Never expose this token to a browser or commit it to git.
"""
import json
import os
import urllib.error
import urllib.parse
import urllib.request


class DialerTransportError(RuntimeError):
    pass


class DialerHTTPAdapter:
    def __init__(self, base_url, token, timeout=12, opener=None):
        parsed = urllib.parse.urlsplit(base_url)
        if parsed.scheme != 'https' or not parsed.netloc or parsed.username or parsed.password or parsed.query or parsed.fragment:
            raise ValueError('Dialer backend must use a clean HTTPS base URL')
        if not token or len(token) < 32:
            raise ValueError('A strong internal API token is required')
        self.endpoint = base_url.rstrip('/') + '/api/internal/provision'
        self.token = token
        self.timeout = timeout
        self.opener = opener or urllib.request.urlopen

    @classmethod
    def from_environment(cls):
        return cls(os.environ.get('DIALER_INTERNAL_URL', ''), os.environ.get('DIALER_PROVISION_TOKEN', ''))

    def provision(self, payload, *, idempotency_key):
        if not isinstance(payload, dict) or not idempotency_key or not isinstance(idempotency_key, str):
            raise ValueError('Valid payload and idempotency key required')
        if len(idempotency_key) > 200 or any(c in idempotency_key for c in '\r\n'):
            raise ValueError('Invalid idempotency key')
        body = json.dumps(payload, separators=(',', ':'), allow_nan=False).encode('utf-8')
        req = urllib.request.Request(self.endpoint, data=body, method='POST', headers={
            'Authorization': 'Bearer ' + self.token,
            'Content-Type': 'application/json',
            'Idempotency-Key': idempotency_key,
        })
        try:
            with self.opener(req, timeout=self.timeout) as response:
                if response.status not in (200, 201):
                    raise DialerTransportError('Unexpected dialer status')
                data = json.loads(response.read(65536))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError, json.JSONDecodeError) as exc:
            raise DialerTransportError('Dialer provisioning request failed') from exc
        account_id = data.get('account_id') if isinstance(data, dict) else None
        if not isinstance(account_id, str) or not account_id.strip():
            raise DialerTransportError('Dialer did not return a valid account ID')
        return account_id


    def pending(self, payload, *, idempotency_key):
        data = dict(payload, pending=True)
        return self.provision(data, idempotency_key=idempotency_key)

    def expire_pending(self, order_reference):
        if not isinstance(order_reference, str) or not order_reference.startswith('DNY-'):
            raise ValueError('Invalid order reference')
        endpoint = self.endpoint.rsplit('/provision', 1)[0] + '/expire-pending'
        req = urllib.request.Request(endpoint, data=json.dumps({'order_reference': order_reference}).encode(), method='POST', headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with self.opener(req, timeout=self.timeout) as response:
                if response.status != 200:
                    raise DialerTransportError('Pending expiry failed')
                result = json.loads(response.read(4096))
        except (urllib.error.URLError, TimeoutError, OSError, ValueError) as exc:
            raise DialerTransportError('Pending expiry request failed') from exc
        if result.get('status') not in ('expired', 'not_found', 'active_protected'):
            raise DialerTransportError('Invalid pending expiry acknowledgement')
        return result['status']
