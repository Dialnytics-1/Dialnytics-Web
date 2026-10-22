"""Owner-approved marketing prices. Never trust a price sent by a browser."""
from decimal import Decimal

CATALOG_VERSION = '2026-10-22.1'
BUSINESS = {
    'brand': 'Dialnytics', 'legal_name': 'PRIME MSM LIMITED',
    'company_number': '17282032',
    'address': 'Office 7264, 58 Peregrine Road, Hainault, Ilford, England, IG6 3SZ',
    'email': 'admin@dialnytics.co.uk', 'whatsapp': '447476629105',
    'phone_display': '+44 7476 629105', 'dialer_url': 'https://dialnytics.co.uk',
    'support_hours': 'Monday-Friday, 3 PM-3 AM the following morning (PKT / UTC+5)',
}
FEATURES = [
    ('calling', 'Unlimited Calling', 'No fixed monthly minute cap within the destinations included in your chosen plan.'),
    ('business-numbers', 'Dedicated Caller ID', 'A dedicated business number, with availability confirmed before activation.'),
    ('crm', 'CRM Integration', 'Keep lead details and calling workflows together.'),
    ('campaigns', 'Power Dialer', 'Work through selected leads with queue controls and call notes.'),
    ('call-logs', 'Call Logs & Analytics', 'Review incoming and outgoing activity and recorded talk time.'),
    ('incoming-calls', 'Incoming & Outgoing', 'Reach customers and receive calls through the browser dialer.'),
    ('call-recording', 'Call Recording', 'Record calls when you have the required permission. Included in every plan.'),
]
PLANS = {
    'usa-canada': {'name': 'USA & Canada', 'short': 'US / CA', 'region': 'North America', 'price': 22, 'from_price': 15, 'description': 'One workspace for conversations across the USA and Canada.', 'code': '+1', 'flag': 'US', 'tone': 'purple'},
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

def price_quote(plan: str, seats: int, countries: list[str] | None = None) -> dict:
    if plan not in PLANS:
        raise ValueError('Choose a valid country plan.')
    if isinstance(seats, bool) or not isinstance(seats, int) or not 1 <= seats <= 100:
        raise ValueError('Choose between 1 and 100 users. Contact us for a larger team.')
    countries = countries or []
    if plan == 'uk-to-europe':
        if not 1 <= len(countries) <= 6 or len(set(countries)) != len(countries):
            raise ValueError('Select 1 to 6 different European destinations, or request a custom quote.')
        if any(c not in EUROPE_COUNTRIES for c in countries):
            raise ValueError('One of the selected destinations is not listed.')
        total = EUROPE_TOTALS[len(countries)] * seats
    elif plan in ('europe', 'custom'):
        total = None
    elif plan == 'usa-canada':
        total = Decimal(22 if seats == 1 else 38 if seats == 2 else 15 * seats)
    else:
        total = Decimal(PLANS[plan]['price']) * seats
    return {'plan': plan, 'plan_name': PLANS[plan]['name'], 'users': seats,
            'countries': countries if plan == 'uk-to-europe' else [],
            'monthly_total': f'{total:.2f}' if total is not None else None,
            'per_user': f'{total / seats:.2f}' if total is not None else None,
            'setup_fee': '0.00', 'extra_charges': '0.00', 'currency': 'USD',
            'catalog_version': CATALOG_VERSION}

def client_catalog() -> dict:
    return {'version': CATALOG_VERSION, 'plans': PLANS, 'europe_totals': {str(k): str(v) for k,v in EUROPE_TOTALS.items()}, 'countries': EUROPE_COUNTRIES}
