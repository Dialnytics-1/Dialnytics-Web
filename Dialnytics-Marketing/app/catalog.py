"""Owner-approved marketing prices. Never trust a price sent by a browser."""
from decimal import Decimal

CATALOG_VERSION = '2026-10-22.1'   # replaced with a version stamp when an admin saves new prices
BUSINESS = {
    'brand': 'Dialnytics', 'legal_name': 'PRIME MSM LIMITED',
    'company_number': '17282032',
    'address': 'Office 7264, 58 Peregrine Road, Hainault, Ilford, England, IG6 3SZ',
    'email': 'admin@dialnytics.co.uk', 'whatsapp': '447476629105',
    'phone_display': '+44 7476 629105', 'dialer_url': 'https://dialnytics.co.uk',
    'support_hours': 'Monday-Friday, 3 PM-3 AM the following morning (PKT / UTC+5)',
}
# Included in every plan. Recording, Power Dialer/Campaigns and SMS are paid add-ons (see ADDONS).
FEATURES = [
    ('calling', 'Unlimited Calling', 'No fixed monthly minute cap within the destinations included in your chosen plan.'),
    ('business-numbers', 'Dedicated Caller ID', 'A dedicated business number, with availability confirmed before activation.'),
    ('call-logs', 'Call Logs & Analytics', 'Review incoming and outgoing activity and talk time.'),
    ('incoming-calls', 'Incoming & Outgoing', 'Reach customers and receive calls through the browser dialer.'),
    ('sms', 'Voicemail', 'Callers can leave a message when you are away. Listen back in the dialer.'),
]
# Optional paid add-ons, priced per user per month (prices are admin-editable; see PRICE_FIELDS).
# 'live': False means shown as "Coming soon" and cannot be ordered.
ADDONS = [
    {'key': 'recording', 'name': 'Call recording', 'field': 'addon_recording', 'live': True, 'page': '/product/call-recording/',
     'note': 'Record calls and play them back or download them from the dialer.'},
    {'key': 'campaigns', 'name': 'CRM + Power Dialer', 'field': 'addon_campaigns', 'live': True, 'page': '/product/campaigns/',
     'note': 'Account-wide combined CRM and Power Dialer package: $10 for one seat or $20 for two or more seats per 30-day period.'},
    {'key': 'sms', 'name': 'SMS texting', 'field': 'addon_sms', 'live': True, 'page': '/product/sms/',
     'note': '300 texts per user each month from your business number. Needs A2P 10DLC registration (one-time fee).'},
    {'key': 'ai', 'name': 'AI call insights', 'field': 'addon_ai', 'live': True, 'page': '/product/ai-insights/',
     'note': 'Summary, transcript and coaching tips after each call.'},
]
ADDON_KEYS = [a['key'] for a in ADDONS]
ORDERABLE_ADDONS = [a['key'] for a in ADDONS if a['live']]
SMS_TEXTS_PER_USER = 300
PLANS = {
    'usa-canada': {'name': 'USA & Canada', 'short': 'US / CA', 'region': 'North America', 'price': 22, 'from_price': 18, 'description': 'One workspace for conversations across the USA and Canada.', 'code': '+1', 'flag': 'US', 'tone': 'purple'},
    'uk': {'name': 'United Kingdom', 'short': 'UK', 'region': 'United Kingdom', 'price': 29, 'from_price': 29, 'description': 'A dedicated presence for your UK conversations.', 'code': '+44', 'flag': 'GB', 'tone': 'blue'},
    'australia': {'name': 'Australia', 'short': 'AU', 'region': 'Asia Pacific', 'price': 44, 'from_price': 44, 'description': 'Bring Australian customer conversations into your browser.', 'code': '+61', 'flag': 'AU', 'tone': 'teal'},
    'japan': {'name': 'Japan', 'short': 'JP', 'region': 'Asia Pacific', 'price': 64, 'from_price': 64, 'description': 'A focused calling plan for teams working with Japan.', 'code': '+81', 'flag': 'JP', 'tone': 'red'},
    'global': {'name': 'Global', 'short': 'Global', 'region': 'International', 'price': 179, 'from_price': 179, 'description': 'One plan for teams with international calling requirements.', 'code': 'Worldwide', 'flag': 'GL', 'tone': 'purple'},
    'uk-to-europe': {'name': 'UK to Europe', 'short': 'UK > EU', 'region': 'Europe', 'price': 44, 'from_price': 44, 'description': 'Use a UK number for your selected European destinations.', 'code': '+44', 'flag': 'EU', 'tone': 'blue'},
    'europe': {'name': 'European Numbers', 'short': 'Europe', 'region': 'Europe', 'price': None, 'from_price': None, 'description': 'Tell us the local number and destinations you need. Receive a tailored quote.', 'code': 'On request', 'flag': 'EU', 'tone': 'teal'},
    'custom': {'name': 'Custom Plan', 'short': 'Custom', 'region': 'Your market', 'price': None, 'from_price': None, 'description': 'A tailored plan for a different destination mix or a larger organisation.', 'code': 'Tailored', 'flag': 'CU', 'tone': 'purple'},
}
EUROPE_COUNTRIES = ['Austria','Belgium','Bulgaria','Croatia','Cyprus','Czech Republic','Denmark','Estonia','Finland','France','Germany','Greece','Hungary','Iceland','Ireland','Italy','Latvia','Lithuania','Luxembourg','Malta','Netherlands','Norway','Poland','Portugal','Romania','Slovakia','Slovenia','Spain','Sweden','Switzerland']
# Published reference totals less USD 1 per user's monthly package, not USD 1 per destination.
# See docs/PRICING.md for the decision and owner-review note.
EUROPE_TOTALS = {1: Decimal('44'), 2: Decimal('79'), 3: Decimal('110.60'), 4: Decimal('137.40'), 5: Decimal('159.85'), 6: Decimal('178.52')}

# ---------------------------------------------------------------- admin-editable prices
# key, label, group, default (USD), minimum, maximum. Defaults are the owner-approved prices above.
PRICE_FIELDS = [
    ('usa_1', '1 user (monthly total)', 'USA & Canada', '22', '1', '1000'),
    ('usa_2', '2 users (monthly total)', 'USA & Canada', '40', '1', '2000'),
    ('usa_per', '3+ users (per user / month)', 'USA & Canada', '18', '1', '1000'),
    ('uk', 'United Kingdom (per user / month)', 'Country plans', '29', '1', '1000'),
    ('australia', 'Australia (per user / month)', 'Country plans', '44', '1', '1000'),
    ('japan', 'Japan (per user / month)', 'Country plans', '64', '1', '1000'),
    ('global', 'Global (per user / month)', 'Country plans', '179', '1', '5000'),
    ('eu_1', '1 destination (per user / month)', 'UK to Europe', '44', '1', '5000'),
    ('eu_2', '2 destinations (per user / month)', 'UK to Europe', '79', '1', '5000'),
    ('eu_3', '3 destinations (per user / month)', 'UK to Europe', '110.60', '1', '5000'),
    ('eu_4', '4 destinations (per user / month)', 'UK to Europe', '137.40', '1', '5000'),
    ('eu_5', '5 destinations (per user / month)', 'UK to Europe', '159.85', '1', '5000'),
    ('eu_6', '6 destinations (per user / month)', 'UK to Europe', '178.52', '1', '5000'),
    ('addon_recording', 'Call recording (per user / month)', 'Add-ons', '5', '0', '1000'),
    ('addon_campaigns', 'CRM + Power Dialer (single account / 30 days)', 'Add-ons', '10', '0', '1000'),
    ('addon_campaigns_team', 'CRM + Power Dialer (team account / 30 days)', 'Add-ons', '20', '0', '1000'),
    ('addon_sms', 'SMS texting (per user / month)', 'Add-ons', '8', '0', '1000'),
    ('addon_ai', 'AI call insights (per user / month)', 'Add-ons', '5', '0', '1000'),
    ('sms_setup', 'SMS registration (one-time, per account)', 'Add-ons', '30', '0', '5000'),
]
DEFAULT_PRICES = {k: Decimal(d) for k, _, _, d, _, _ in PRICE_FIELDS}
PRICES = dict(DEFAULT_PRICES)

def clean_prices(raw: dict) -> dict:
    """Validate admin input. Returns Decimals with at most 2 decimal places; raises ValueError with a readable message."""
    out = {}
    for key, label, group, default, lo, hi in PRICE_FIELDS:
        value = str(raw.get(key, '')).strip().replace('$', '').replace(',', '')
        try:
            d = Decimal(value)
        except Exception:
            raise ValueError(f'{group} - {label}: enter a number.')
        if not d.is_finite() or d != d.quantize(Decimal('0.01')):
            raise ValueError(f'{group} - {label}: use at most 2 decimal places.')
        if not Decimal(lo) <= d <= Decimal(hi):
            raise ValueError(f'{group} - {label}: must be between {lo} and {hi}.')
        out[key] = d.quantize(Decimal('0.01'))
    return out

def apply_prices(values: dict, version: str | None = None) -> None:
    """Update the in-memory catalog in place so every importer (pages, calculator, quotes, chatbot) sees the new prices."""
    global CATALOG_VERSION
    merged = dict(DEFAULT_PRICES); merged.update({k: Decimal(str(v)) for k, v in (values or {}).items() if k in DEFAULT_PRICES})
    PRICES.clear(); PRICES.update(merged)
    num = lambda d: int(d) if d == d.to_integral_value() else float(d)
    PLANS['usa-canada']['price'] = num(merged['usa_1']); PLANS['usa-canada']['from_price'] = num(merged['usa_per'])
    for slug in ('uk', 'australia', 'japan', 'global'):
        PLANS[slug]['price'] = PLANS[slug]['from_price'] = num(merged[slug])
    PLANS['uk-to-europe']['price'] = PLANS['uk-to-europe']['from_price'] = num(merged['eu_1'])
    EUROPE_TOTALS.clear(); EUROPE_TOTALS.update({n: merged['eu_' + str(n)] for n in range(1, 7)})
    if version: CATALOG_VERSION = version

def usd(value) -> str:
    """22 -> '22', 110.6 -> '110.60'."""
    d = Decimal(str(value))
    return str(int(d)) if d == d.to_integral_value() else f'{d:.2f}'

def price_view() -> dict:
    """Ready-to-print prices for templates."""
    p = PRICES
    return {'usa_1': usd(p['usa_1']), 'usa_2': usd(p['usa_2']), 'usa_per': usd(p['usa_per']),
            'usa_3_total': usd(p['usa_per'] * 3), 'usa_5_total': usd(p['usa_per'] * 5),
            'uk': usd(p['uk']), 'australia': usd(p['australia']), 'japan': usd(p['japan']), 'global': usd(p['global']),
            'eu_1': usd(p['eu_1']),
            'addon_recording': usd(p['addon_recording']), 'addon_campaigns': usd(p['addon_campaigns']), 'addon_campaigns_team': usd(p['addon_campaigns_team']),
            'addon_sms': usd(p['addon_sms']), 'addon_ai': usd(p['addon_ai']), 'sms_setup': usd(p['sms_setup']),
            'from': usd(min(p['usa_per'], p['uk'], p['australia'], p['japan'], p['global'])),
            'sms_texts': SMS_TEXTS_PER_USER}

def addon_view() -> list:
    """Add-ons with their current price, for templates."""
    return [{**a, 'price': usd(PRICES[a['field']]), 'team_price': usd(PRICES['addon_campaigns_team']) if a['key'] == 'campaigns' else None, 'billing_scope': 'account' if a['key'] == 'campaigns' else 'seat'} for a in ADDONS]

def price_quote(plan: str, seats: int, countries: list[str] | None = None, addons: list[str] | None = None) -> dict:
    if plan not in PLANS:
        raise ValueError('Choose a valid country plan.')
    if isinstance(seats, bool) or not isinstance(seats, int) or not 1 <= seats <= 100:
        raise ValueError('Choose between 1 and 100 users. Contact us for a larger team.')
    countries = countries or []
    addons = list(addons or [])
    if not isinstance(addons, list) or any(not isinstance(a, str) for a in addons) or len(set(addons)) != len(addons):
        raise ValueError('Choose valid add-ons.')
    if any(a not in ADDON_KEYS for a in addons):
        raise ValueError('Choose valid add-ons.')
    if any(a not in ORDERABLE_ADDONS for a in addons):
        raise ValueError('AI insights is coming soon and cannot be ordered yet.')
    addons = [k for k in ADDON_KEYS if k in addons]  # stable order
    if plan == 'uk-to-europe':
        if not 1 <= len(countries) <= 6 or len(set(countries)) != len(countries):
            raise ValueError('Select 1 to 6 different European destinations, or request a custom quote.')
        if any(c not in EUROPE_COUNTRIES for c in countries):
            raise ValueError('One of the selected destinations is not listed.')
        total = EUROPE_TOTALS[len(countries)] * seats
    elif plan in ('europe', 'custom'):
        total = None
    elif plan == 'usa-canada':
        total = PRICES['usa_1'] if seats == 1 else PRICES['usa_2'] if seats == 2 else PRICES['usa_per'] * seats
    else:
        total = Decimal(PLANS[plan]['price']) * seats
    by_key = {a['key']: a for a in ADDONS}
    lines = [{'key': k, 'name': by_key[k]['name'], 'per_user': f"{(PRICES['addon_campaigns_team'] if seats > 1 else PRICES['addon_campaigns']) if k == 'campaigns' else PRICES[by_key[k]['field']]:.2f}",
              'total': f"{(PRICES['addon_campaigns_team'] if seats > 1 else PRICES['addon_campaigns']) if k == 'campaigns' else PRICES[by_key[k]['field']] * seats:.2f}"} for k in addons]
    addons_total = sum(((PRICES['addon_campaigns_team'] if seats > 1 else PRICES['addon_campaigns']) if k == 'campaigns' else PRICES[by_key[k]['field']] * seats for k in addons), Decimal('0'))
    one_time = PRICES['sms_setup'] if 'sms' in addons else Decimal('0')
    monthly = total + addons_total if total is not None else None
    return {'plan': plan, 'plan_name': PLANS[plan]['name'], 'users': seats,
            'countries': countries if plan == 'uk-to-europe' else [],
            'plan_total': f'{total:.2f}' if total is not None else None,
            'per_user': f'{total / seats:.2f}' if total is not None else None,
            'addons': lines, 'addons_total': f'{addons_total:.2f}',
            'monthly_total': f'{monthly:.2f}' if monthly is not None else None,
            'one_time_total': f'{one_time:.2f}',
            'first_payment': f'{monthly + one_time:.2f}' if monthly is not None else None,
            'setup_fee': '0.00', 'extra_charges': '0.00', 'taxes_included': True, 'currency': 'USD',
            'catalog_version': CATALOG_VERSION}

def client_catalog() -> dict:
    return {'version': CATALOG_VERSION, 'plans': PLANS, 'europe_totals': {str(k): str(v) for k,v in EUROPE_TOTALS.items()}, 'countries': EUROPE_COUNTRIES,
            'usa': {'one': str(PRICES['usa_1']), 'two': str(PRICES['usa_2']), 'per': str(PRICES['usa_per'])},
            'addons': [{'key': a['key'], 'name': a['name'], 'price': str(PRICES[a['field']]), 'team_price': str(PRICES['addon_campaigns_team']) if a['key'] == 'campaigns' else None, 'billing_scope': 'account' if a['key'] == 'campaigns' else 'seat', 'live': a['live'], 'note': a['note']} for a in ADDONS],
            'sms_setup': str(PRICES['sms_setup'])}
