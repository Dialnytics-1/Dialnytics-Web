"""Server-to-server client for the dialer (https://dialnytics.co.uk).

All provider keys stay on the dialer. This site only sends the shared secret in the X-Marketing-Key
header. Passwords are forwarded once and never stored here.
"""
import json, logging, urllib.error, urllib.parse, urllib.request

log = logging.getLogger('dialnytics.dialer')

class DialerError(Exception):
    """status 0 = dialer unreachable; otherwise the dialer's HTTP status. `detail` is safe to show to a buyer."""
    def __init__(self, status: int, detail: str):
        super().__init__(detail); self.status = status; self.detail = detail

class Dialer:
    def __init__(self, settings): self.s = settings

    def _call(self, method, path, body=None, timeout=25):
        if not self.s.dialer_ready: raise DialerError(0, 'Number selection is temporarily unavailable. Please contact us on WhatsApp.')
        data = json.dumps(body).encode() if body is not None else None
        req = urllib.request.Request(self.s.dialer_api_url + '/webhooks/marketing' + path, data=data, method=method,
                                     headers={'X-Marketing-Key': self.s.dialer_api_key, 'Content-Type': 'application/json'})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r: return json.loads(r.read() or b'{}')
        except urllib.error.HTTPError as e:
            raw = e.read()[:2000].decode('utf-8', 'replace')
            try: detail = json.loads(raw).get('detail', '')
            except Exception: detail = ''
            if isinstance(detail, list): detail = '; '.join(str(x.get('msg', x)) for x in detail)
            log.warning('Dialer %s %s -> %s', method, path.split('?')[0], e.code)
            raise DialerError(e.code, str(detail) or 'The dialer refused this request.')
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            log.error('Dialer unreachable (%s %s): %s', method, path.split('?')[0], type(e).__name__)
            raise DialerError(0, 'Number selection is temporarily unavailable. Please try again or contact us on WhatsApp.')

    def numbers(self, plan, toll_free, token=''):
        q = urllib.parse.urlencode({'plan': plan, 'toll_free': 1 if toll_free else 0, 'token': token})
        return self._call('GET', '/numbers?' + q).get('numbers', [])
    def hold(self, token, plan, numbers, toll_free): return self._call('POST', '/hold', {'token': token, 'plan': plan, 'numbers': numbers, 'toll_free': bool(toll_free)})
    def create_order(self, body): return self._call('POST', '/orders', body, timeout=60)   # hashing many passwords takes a moment
    def paid(self, ref, method, amount_usd, reference=''): return self._call('POST', f'/orders/{ref}/paid', {'method': method, 'amount_usd': amount_usd, 'reference': reference}, timeout=60)
    def renew(self, ref, amount_usd, reference=''): return self._call('POST', f'/orders/{ref}/renew', {'amount_usd': amount_usd, 'reference': reference})
    def cancel(self, ref): return self._call('POST', f'/orders/{ref}/cancel', {})
    def status(self, ref): return self._call('GET', f'/orders/{ref}')
