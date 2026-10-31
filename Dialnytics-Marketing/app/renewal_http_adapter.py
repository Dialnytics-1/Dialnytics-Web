"""Authenticated renewal synchronization to the dialer (server-side only)."""
import json
import urllib.error
import urllib.parse
import urllib.request
from datetime import date, datetime


class RenewalHTTPError(RuntimeError):
    pass


class RenewalHTTPAdapter:
    def __init__(self, base_url, token, opener=None, timeout=12):
        url = urllib.parse.urlsplit(base_url)
        if url.scheme != 'https' or not url.netloc or url.username or url.password or url.query or url.fragment:
            raise ValueError('HTTPS dialer backend URL required')
        if not token or len(token) < 32:
            raise ValueError('Strong internal token required')
        self.url = base_url.rstrip('/') + '/api/internal/renewal-sync'
        self.token = token
        self.opener = opener or urllib.request.urlopen
        self.timeout = timeout

    def sync(self, account_id, paid_through):
        if isinstance(paid_through, datetime):
            paid_through = paid_through.date()
        if not isinstance(paid_through, date):
            raise ValueError('paid_through must be a date')
        body = json.dumps({'account_id': str(account_id), 'paid_through': paid_through.isoformat()}).encode()
        request = urllib.request.Request(self.url, data=body, method='POST', headers={
            'Authorization': 'Bearer ' + self.token, 'Content-Type': 'application/json'})
        try:
            with self.opener(request, timeout=self.timeout) as response:
                if response.status != 200:
                    raise RenewalHTTPError('Dialer renewal sync rejected')
                result = json.loads(response.read(8192))
        except (urllib.error.URLError, OSError, TimeoutError, ValueError) as exc:
            raise RenewalHTTPError('Dialer renewal sync failed') from exc
        if not isinstance(result, dict) or result.get('status') != 'synced' or result.get('account_id') != str(account_id):
            raise RenewalHTTPError('Unexpected renewal acknowledgement')
        if result.get('paid_through', '') < paid_through.isoformat():
            raise RenewalHTTPError('Dialer did not apply paid-through date')
        return result
