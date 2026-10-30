"""Dialnytics AI customer-service assistant: knowledge, Claude API calls, lead fields,
and Telnyx WhatsApp helpers. No database code here (see chat_routes.py)."""
import base64, json, logging, re, time, uuid, urllib.request, urllib.error, urllib.parse
from dataclasses import dataclass, field
from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric.ed25519 import Ed25519PublicKey
from .catalog import BUSINESS, PLANS, FEATURES, EUROPE_TOTALS, price_quote, usd

log = logging.getLogger('dialnytics.chatbot')
ANTHROPIC_URL = 'https://api.anthropic.com/v1/messages'
TELNYX_WA_URL = 'https://api.telnyx.com/v2/messages/whatsapp'
REQUIRED_FIELDS = ('name', 'email', 'whatsapp', 'campaign_name')  # what the team needs to create the account
ORDER = ('request', 'name', 'email', 'whatsapp', 'campaign_name', 'company', 'calling_country', 'users', 'plan_interest', 'notes')
REQUESTS = {'purchase': 'Wants to buy', 'info': 'Enquiry'}
FIELD_LABELS = {'name': 'Name', 'whatsapp': 'WhatsApp number', 'company': 'Company name',
                'calling_country': 'Calling country', 'users': 'Users needed', 'email': 'Email',
                'plan_interest': 'Plan interest', 'notes': 'Notes',
                'campaign_name': 'Campaign name', 'request': 'Request'}

# ---------------------------------------------------------------- fixed texts
LANG_MENU = ("Welcome to Dialnytics! 👋\nPlease choose your language:\n1. English\n2. Roman Urdu\n\n"
             "Reply 1 or 2.")
GREETING = {
    'en': "Great! I'm the Dialnytics virtual assistant. I can help with plans, prices and getting your "
          "business calling set up. What would you like to know?",
    'ur': "Zabardast! Main Dialnytics ka virtual assistant hoon. Plans, prices aur aap ki business calling "
          "setup karne mein madad kar sakta hoon. Bataiye, aap kya janna chahte hain?",
}
FALLBACK = {
    'en': "Sorry, I'm having a short delay. Our team has been notified and will reply here shortly.",
    'ur': "Maazrat, abhi thori der ho rahi hai. Hamari team ko bata diya gaya hai, woh jald yahin jawab degi.",
}
LIMIT_REACHED = {
    'en': "Thank you! Our team will continue this conversation with you personally.",
    'ur': "Shukriya! Ab hamari team khud aap se baat aage barhayegi.",
}
PAUSED_NOTE = {
    'en': "Thanks, our team has your message and will reply here.",
    'ur': "Shukriya, aap ka message team tak pohanch gaya hai, woh yahin jawab degi.",
}

def language_choice(text: str):
    t = (text or '').strip().lower().strip('.!) ')
    if t in ('1', 'english', 'eng', 'en', 'english please', '1 english'): return 'en'
    if t in ('2', 'urdu', 'roman urdu', 'roman', 'ur', '2 roman urdu', 'urdu please', 'اردو'): return 'ur'
    return None

_UR_WORDS = {'kya', 'hai', 'hain', 'ka', 'ki', 'ke', 'mujhe', 'mujhy', 'chahiye', 'chahye', 'kitne', 'kitny',
             'aap', 'ap', 'kaise', 'kese', 'krna', 'karna', 'kr', 'nahi', 'ni', 'haan', 'han', 'acha', 'theek',
             'bhai', 'salam', 'assalam', 'kitna', 'kab', 'kahan', 'kyun', 'mein', 'mai', 'hum', 'tum', 'batao',
             'liye', 'mujy', 'mjhe', 'rha', 'raha', 'kro', 'karo', 'hy', 'chahte', 'chahta', 'bata', 'dein', 'krna', 'krein'}

def guess_language(text: str) -> str:
    words = set(re.findall(r'[a-z]+', (text or '').lower()))
    if re.search(r'[؀-ۿ]', text or ''): return 'ur'
    return 'ur' if len(words & _UR_WORDS) >= 2 else 'en'

# ---------------------------------------------------------------- knowledge
def _ex(slug, users=1):
    """Example price for prompt wording, always taken from the live (admin-managed) catalog."""
    from decimal import Decimal
    return usd(Decimal(str(PLANS[slug]['price'])) * users)

def _usa_line():
    one, two, three = (price_quote('usa-canada', n) for n in (1, 2, 3))
    return (f"USA & Canada: 1 user ${one['monthly_total']}/month; 2 users ${two['monthly_total']} total/month; "
            f"3 or more users ${three['per_user']} per user/month (e.g. 3 users = ${three['monthly_total']}, "
            f"5 users = ${price_quote('usa-canada', 5)['monthly_total']}).")

def knowledge(base_url: str) -> str:
    lines = ['PRICES (USD per month, taxes included, no setup fee; optional paid add-ons listed below):',
             '- ' + _usa_line()]
    for slug in ('uk', 'australia', 'japan', 'global'):
        p = PLANS[slug]
        lines.append(f"- {p['name']}: ${p['price']} per user/month. Plan page: {base_url}/numbers/{slug}/")
    eu = ', '.join(f"{k} countr{'y' if k == 1 else 'ies'} ${v}" for k, v in EUROPE_TOTALS.items())
    lines.append(f"- UK to Europe (UK number calling selected European countries): per user/month by number of "
                 f"destinations: {eu}.")
    lines.append('- European local numbers and Custom plans: tailored quote from the team.')
    lines.append(f'- Full pricing and calculator: {base_url}/pricing/')
    lines.append('FEATURES INCLUDED IN EVERY PLAN:')
    lines += [f'- {name}: {desc}' for _, name, desc in FEATURES]
    from .catalog import ADDONS, PRICES, usd as _usd
    lines.append('OPTIONAL PAID ADD-ONS (per user per month, added on top of the plan price; NOT included by default):')
    for a in ADDONS:
        price = _usd(PRICES[a['field']])
        if a['live']:
            extra = f" plus a one-time ${_usd(PRICES['sms_setup'])} registration per account" if a['key'] == 'sms' else ''
            lines.append(f"- {a['name']}: ${price} per user/month{extra}. {a['note']}")
        else:
            lines.append(f"- {a['name']}: COMING SOON, cannot be ordered yet (planned ${price} per user/month).")
    lines.append('Example: UK plan 2 users with Call recording = 2 x (UK price + recording price) per month.')
    lines += [
        'Calling works in the browser (computer or phone browser), no SIM or app needed. Use a headset for best quality.',
        'HOW IT WORKS: customer shares details -> team confirms number availability and requirements on WhatsApp '
        '-> payment -> account activated 24/7 within 10-15 minutes after payment confirmation -> login details sent.',
        'PAYMENT: Bank Transfer, USDT, or Credit/Debit card via a secure Stripe link. The team sends payment '
        'instructions on WhatsApp. The website/chat never takes payment.',
        'DEMO ACCOUNT / FREE TRIAL: NOT available. Instead offer the product tour: ' + base_url + '/product/tour/ '
        '(full walkthrough of the dialer in under 5 minutes) and answer their questions.',
        'TO BUY: the customer shares Full Name, Email Address, Phone Number and Campaign Name; once these are received '
        'and payment is confirmed, the account is activated within 10-15 minutes.',
        'NUMBERS: a dedicated caller ID is included; the team confirms availability of a preferred country/area '
        'before payment. A chat does not reserve a number.',
        f"SUPPORT HOURS: {BUSINESS['support_hours']}. Activation is 24/7, separate from support hours.",
        f"EXISTING CUSTOMERS sign in at {BUSINESS['dialer_url']} (Client Login).",
        f"CONTACT: WhatsApp {BUSINESS['phone_display']}, email {BUSINESS['email']}. Operated by "
        f"{BUSINESS['legal_name']} (UK company {BUSINESS['company_number']}). Registered office: {BUSINESS['address']} "
        "(registered office only, not a walk-in support location; support is online via WhatsApp/email).",
        'REFUNDS: final written refund/cancellation terms are provided by the team before payment; do not promise refunds.',
        'VOICEMAIL is included. SMS texting is a live paid add-on (US texting needs A2P 10DLC business registration). '
        'NOT CONFIRMED IN CHAT: AI transcripts/live captions/Floating Phone (coming soon), discounts, minimum contracts, '
        'specific number availability. For these say the team will confirm.',
    ]
    return '\n'.join(lines)

def system_prompt(language: str, channel: str, lead: dict, base_url: str) -> str:
    lang_rule = ("Do NOT ask which language they prefer. Mirror the customer's own style in every reply: "
                 "if they write in English, reply in clear simple English; if they write in Roman Urdu or a mix of "
                 "Roman Urdu and English (the normal Pakistani chat style, e.g. 'Han mujhe Japan ke liye 2 user ka dialer chahiye'), "
                 f"reply in the same natural mix, e.g. 'Ji bilkul! Japan plan ${_ex('japan')} per user/month hai, to 2 users ka total "
                 f"${_ex('japan', 2)}/month banega. Aap ka naam kya hai?'. Keep business words (plan, users, price, number, setup) in English. "
                 "Never use Urdu/Arabic script. Use 'aap', polite and friendly. If they greet with Salam, reply Walaikum Assalam.")
    have = {k: v for k, v in (lead or {}).items() if v not in (None, '')}
    missing = [FIELD_LABELS[f] for f in REQUIRED_FIELDS if f not in have]
    channel_rule = ("This chat is on WHATSAPP. The customer's WhatsApp number is already known; do not ask for it. "
                    "Keep replies very short (1-4 short lines). You may use *bold* sparingly. No tables."
                    if channel == 'whatsapp' else
                    "This chat is the WEBSITE chat widget. Plain text only: no markdown, no **, no #, no tables. "
                    "Keep replies short (1-5 short lines). When they are interested, naturally ask for their WhatsApp number with country code so the team can send number options.")
    wa_phone_line = ('\n   On WhatsApp write "Phone Number (agar yahi WhatsApp number hai to bas same likh dein)". '
                     'If they say same, the known WhatsApp number is their phone; do not ask for it again.'
                     if channel == 'whatsapp' else '')
    return f"""You are the Dialnytics virtual assistant, chatting with potential customers for Dialnytics, a business calling platform (browser dialer with dedicated caller ID, unlimited calling, CRM and voicemail, plus optional add-ons: call recording, Campaigns & Power Dialer and SMS). Talk like an experienced, friendly sales person from the team: relaxed, helpful, human. Never like a form or a bot.

LANGUAGE: {lang_rule}
CHANNEL: {channel_rule}

HOW TO TALK (most important):
- First HELP, then ask. Always answer what the customer actually said, using every detail they gave. Example: they say "UK ke liye 3 dialer chahiye" -> confirm and quote right away: "Ji bilkul! UK plan ${_ex('uk')} per user/month hai, to 3 users ka total ${_ex('uk', 3)}/month banega. Is mein unlimited UK calling, apna UK number, CRM aur voicemail included hai, koi setup fee nahi. Call recording ya Power Dialer chahiye to add-on le sakte hain." Then ONE easy follow-up question.
- Never ignore their message to ask for data. Never ask for name and company together. Never say things like "taake hum details save kar sakein" or "please provide your details".
- Ask only ONE short question per message, and only when it fits the flow. Good natural questions: "Aap ki team kahan se kaam karti hai?", "Kab tak start karna chahte hain?", "Waise main aap ko kis naam se address karun?", "Aap ki company ka naam kya hai, taake team number setup ke liye ready rakhe?"
- Useful to learn naturally during normal chat (one at a time, skip what they told you): name, calling country, number of users, company. If the customer is just exploring, answer and do not push. The full account details (name, email, phone, campaign name) are collected with the checklist in step 4.
- On a simple greeting ("Hi", "Salam"), greet back warmly and ask how you can help (e.g. "Walaikum Assalam! Bataiye, main kaise madad kar sakta hoon?"). Do not immediately ask which country.
- Match their energy and length. Short, warm sentences. Vary your wording; do not repeat the same opener. A light emoji now and then is fine, not in every message.
- If a message is unclear (e.g. just "?"), look at the earlier messages and answer what they most likely meant (often: they are waiting for an answer to their last question).
- If they hesitate (price, trust, "sochta hoon"), be understanding, give one useful reason (no setup fee, taxes included, activation in 10-15 minutes, product tour link), no pressure.

WHAT YOU DO:
1. Answer accurately using ONLY the knowledge below. Never invent prices, discounts, trials, features, refund terms, timelines or number availability. If something is not in the knowledge, say the team will confirm it.
2. Quote the correct monthly total whenever you know the plan and user count (compute it from the price rules).
3. Call the save_lead tool whenever the customer shares any of these details (you may call it several times). ALWAYS write your reply to the customer in the SAME response as the tool call. Never mention saving or the tool.
4. READY TO BUY: use your judgement. Send the checklist as soon as the customer clearly SHOWS they want to buy, even if they never say the word "purchase". Buying signals: "ok le leta hoon", "theek hai done", "kaise start karein?", "payment kaise karun?", "account bana do", "number kab milega?", "kitni der mein active hoga?", agreeing after you quote a price, or confirming a plan and user count. NOT buying signals yet: only asking prices, comparing plans, asking features, "sochta hoon", "baad mein batata hoon" - then just help and do not send the list. Do not send the checklist twice; if some details are still missing later, ask only for those, briefly.
   When ready, send the team's standard checklist in ONE message (this is the one time a list of details is fine), in the customer's language style, listing ONLY what you do not know yet. English example:
   "Sure! To create your account, please share the following details:
   - Full Name
   - Email Address
   - Phone Number
   - Campaign Name
   Once I receive these details and your payment is confirmed, your account will be activated within 10-15 minutes."
   Roman Urdu/mix example: "Ji zaroor! Account create karne ke liye ye details share kar dein: ... Ye details milne aur payment confirm hone ke baad aap ka account 10-15 minute mein activate ho jayega."{wa_phone_line}
   Campaign Name = the name they want for their calling campaign/account (often their business or project name). If they are unsure, suggest using their company name.
   Set request to purchase in save_lead.
5. When name, email, phone and campaign name are known, confirm warmly: the team will message them on WhatsApp with the payment details, and the account is activated within 10-15 minutes after payment confirmation. Do not ask for anything else after that unless they want to continue.
   DEMO ACCOUNT / FREE TRIAL requests: politely say it is not available, share the product tour, and offer to answer any question; if they then want to buy, use step 4.
6. Also share the product tour {base_url}/product/tour/ when they want to see how it works.
7. If the customer asks for a human, is upset, has an account/technical problem you cannot solve, or wants something not covered, call request_human and tell them the team will reply here (mention support hours if outside them).

RULES:
- Never mention telecom carriers, underlying providers or technology vendors, and never name the AI company or model behind you. If asked whether you are a bot, honestly say you are Dialnytics' AI assistant and a human from the team can join any time.
- Never ask for or accept card numbers, CVV, passwords, OTPs or recovery phrases. If shared, tell them not to share it.
- Stay on topic (Dialnytics, business calling). Politely decline unrelated requests.
- You can only read text. If a message is like '[image received]' or '[audio received]', ask the customer to type it.

ALREADY SAVED: {json.dumps(have, ensure_ascii=False) if have else 'nothing yet'}
STILL UNKNOWN (learn naturally over the chat, never all at once): {', '.join(missing) if missing else 'nothing - all details known'}

KNOWLEDGE:
{knowledge(base_url)}"""

TOOLS = [
    {'name': 'save_lead',
     'description': 'Save or update details the customer has shared. Include only fields the customer actually gave.',
     'input_schema': {'type': 'object', 'properties': {
         'name': {'type': 'string', 'description': "Customer's full name"},
         'company': {'type': 'string', 'description': 'Company / business name'},
         'whatsapp': {'type': 'string', 'description': 'WhatsApp number in international format, e.g. +447700900123'},
         'calling_country': {'type': 'string', 'description': 'Country or countries they want to call'},
         'users': {'type': 'integer', 'description': 'Number of users (agents) needed'},
         'email': {'type': 'string', 'description': 'Email address (optional)'},
         'plan_interest': {'type': 'string', 'description': 'Plan they are interested in, if clear'},
         'campaign_name': {'type': 'string', 'description': 'Campaign name for their account'},
         'request': {'type': 'string', 'enum': ['purchase', 'info'], 'description': 'What they want'},
         'notes': {'type': 'string', 'description': 'One short line about their needs or use case'}},
         'additionalProperties': False}},
    {'name': 'request_human',
     'description': 'Hand the conversation to the Dialnytics team (customer asks for a human, complaint, account problem, or unanswerable question).',
     'input_schema': {'type': 'object', 'properties': {'reason': {'type': 'string'}}, 'required': ['reason'],
                      'additionalProperties': False}},
]

# ---------------------------------------------------------------- lead fields
def normalize_phone(value: str):
    raw = re.sub(r'[\s().-]', '', str(value or ''))
    if raw.startswith('00'): raw = '+' + raw[2:]
    if re.fullmatch(r'\+[1-9]\d{7,14}', raw): return raw
    return None

def clean_lead(data: dict):
    """Validate a save_lead tool input. Returns (updates, errors)."""
    updates, errors = {}, []
    for key in ('name', 'company', 'calling_country', 'plan_interest', 'notes', 'campaign_name'):
        if key in data and str(data[key]).strip():
            updates[key] = re.sub(r'[\x00-\x1f]', ' ', str(data[key])).strip()[:150 if key != 'notes' else 400]
    if data.get('request') in REQUESTS: updates['request'] = data['request']
    if data.get('whatsapp'):
        phone = normalize_phone(data['whatsapp'])
        if phone: updates['whatsapp'] = phone
        else: errors.append('whatsapp: invalid - ask for the number with country code, e.g. +44 7700 900123')
    if data.get('email'):
        email = str(data['email']).strip().lower()[:254]
        if re.fullmatch(r'[^@\s]+@[^@\s]+\.[a-z]{2,}', email): updates['email'] = email
        else: errors.append('email: invalid - ask them to check it')
    if 'users' in data and data['users'] not in (None, ''):
        try:
            users = int(data['users'])
            if not 1 <= users <= 1000: raise ValueError
            updates['users'] = users
        except (TypeError, ValueError):
            errors.append('users: must be a whole number between 1 and 1000')
    return updates, errors

def missing_fields(lead: dict):
    return [f for f in REQUIRED_FIELDS if (lead or {}).get(f) in (None, '')]

# ---------------------------------------------------------------- Claude API
def to_api_messages(rows, limit=40):
    """rows: iterable of (role, body) oldest first. Returns alternating user/assistant messages."""
    out = []
    for role, body in list(rows)[-limit:]:
        if role not in ('user', 'assistant', 'admin') or not (body or '').strip(): continue
        api_role = 'user' if role == 'user' else 'assistant'
        text = body.strip()[:2000]
        if out and out[-1]['role'] == api_role: out[-1]['content'] += '\n\n' + text
        else: out.append({'role': api_role, 'content': text})
    while out and out[0]['role'] != 'user': out.pop(0)
    if not out or out[-1]['role'] != 'user': return []
    return out

FAST_MODE = {'ok': True}  # switched off automatically if the model rejects the speed settings

def call_anthropic(api_key, model, system, messages, tools, timeout=40, tool_choice=None):
    payload = {'model': model, 'max_tokens': 700, 'system': system, 'messages': messages, 'tools': tools}
    if tool_choice: payload['tool_choice'] = {'type': tool_choice}
    if FAST_MODE['ok']:
        # Adaptive thinking at low effort: easy questions are answered without thinking (fast);
        # the model still thinks when a question is unclear or complicated.
        payload.update(thinking={'type': 'adaptive'}, output_config={'effort': 'low'})
    headers = {'x-api-key': api_key, 'anthropic-version': '2023-06-01', 'content-type': 'application/json'}
    last = None
    for attempt in range(3):
        req = urllib.request.Request(ANTHROPIC_URL, data=json.dumps(payload).encode(), method='POST', headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=timeout) as res:
                return json.loads(res.read().decode())
        except urllib.error.HTTPError as exc:
            last = exc
            detail = exc.read()[:400].decode('utf-8', 'replace')
            log.warning('AI API HTTP %s: %s', exc.code, detail)
            if exc.code == 400 and 'thinking' in payload and any(w in detail for w in ('thinking', 'effort', 'output_config')):
                FAST_MODE['ok'] = False
                payload.pop('thinking', None); payload.pop('output_config', None)
                continue
            if exc.code not in (429, 500, 502, 503, 529): break
        except (urllib.error.URLError, TimeoutError, OSError) as exc:
            last = exc
            log.warning('AI API connection error: %s', type(exc).__name__)
        time.sleep(1.5)
    raise RuntimeError('AI request failed: ' + type(last).__name__)

@dataclass
class AIResult:
    text: str = ''
    lead_updates: dict = field(default_factory=dict)
    human: str = ''
    error: bool = False

def run_ai(settings, rows, language, channel, lead, base_url, caller=call_anthropic):
    """One assistant turn. `rows` are (role, body) pairs. `caller` is injectable for tests."""
    result = AIResult()
    messages = to_api_messages(rows)
    if not messages: return result
    current = dict(lead or {})
    earlier = ''
    try:
        # Build the system prompt ONCE per turn: tool-use follow-up calls must send the exact same
        # prefix, otherwise the API rejects the returned thinking-block signatures.
        system = system_prompt(language or 'en', channel, current, base_url)
        for _ in range(4):
            resp = caller(settings.anthropic_key, settings.ai_model, system, messages, TOOLS)
            blocks = resp.get('content') or []
            texts = [b.get('text', '') for b in blocks if b.get('type') == 'text' and b.get('text', '').strip()]
            uses = [b for b in blocks if b.get('type') == 'tool_use']
            if texts: result.text = '\n\n'.join(t.strip() for t in texts)
            if resp.get('stop_reason') != 'tool_use' or not uses: break
            outputs, needs_followup = [], not texts
            for use in uses:
                if use.get('name') == 'save_lead':
                    updates, errors = clean_lead(use.get('input') or {})
                    result.lead_updates.update(updates); current.update(updates)
                    if errors: needs_followup = True
                    out = {'saved': sorted(updates), 'errors': errors,
                           'still_needed': [FIELD_LABELS[f] for f in missing_fields(current)]}
                elif use.get('name') == 'request_human':
                    result.human = str((use.get('input') or {}).get('reason', 'Customer asked for the team'))[:300]
                    out = {'ok': True, 'note': 'Team notified. Tell the customer the team will reply here.'}
                else:
                    out = {'error': 'unknown tool'}; needs_followup = True
                outputs.append({'type': 'tool_result', 'tool_use_id': use.get('id'), 'content': json.dumps(out)})
            if not needs_followup: break  # the reply was already written alongside the tool call
            messages = messages + [{'role': 'assistant', 'content': blocks}, {'role': 'user', 'content': outputs}]
            earlier = result.text or earlier
            result.text = ''  # the follow-up response carries the reply
    except Exception:
        log.exception('AI turn failed')
        result.error = True
        result.text = FALLBACK.get(language or 'en', FALLBACK['en'])
        return result
    if not result.text.strip():
        result.text = earlier
    if not result.text.strip():
        # The model ended without writing anything (it happens after a tool call): ask once more for text only.
        log.warning('AI returned no text; asking again without tools')
        try:
            resp = caller(settings.anthropic_key, settings.ai_model, system, messages, TOOLS, tool_choice='none')
            result.text = '\n\n'.join(b.get('text', '').strip() for b in (resp.get('content') or [])
                                       if b.get('type') == 'text' and b.get('text', '').strip())
        except Exception:
            log.exception('AI retry failed')
        if not result.text.strip():
            result.error = True
            result.text = FALLBACK.get(language or 'en', FALLBACK['en'])
    result.text = clean_reply(result.text, channel)
    return result

_VENDOR = re.compile(r'\b(telnyx|twilio|anthropic|claude|openai|chatgpt)\b', re.I)

def clean_reply(text: str, channel: str) -> str:
    text = (text or '').strip()
    text = _VENDOR.sub('our system', text)
    if channel != 'whatsapp':
        text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
        text = re.sub(r'^#+\s*', '', text, flags=re.M)
    return text[:3000]

# ---------------------------------------------------------------- Telnyx WhatsApp
# Result of the latest WhatsApp send, shown on Admin > Chats to help diagnose delivery problems.
LAST_SEND = {'at': None, 'ok': None, 'detail': ''}

def _record_send(ok, detail=''):
    LAST_SEND.update({'at': time.time(), 'ok': ok, 'detail': (detail or '')[:300]})

def _telnyx_post(settings, payload, timeout=20):
    req = urllib.request.Request(TELNYX_WA_URL, data=json.dumps(payload).encode(), method='POST', headers={
        'Authorization': 'Bearer ' + settings.telnyx_key, 'Content-Type': 'application/json',
        'Accept': 'application/json', 'Idempotency-Key': str(uuid.uuid4())})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as res:
            data = json.loads(res.read().decode() or '{}')
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:400].decode('utf-8', 'replace')
        log.warning('WhatsApp send HTTP %s: %s', exc.code, detail)
        try: nice = '; '.join(e.get('detail') or e.get('title', '') for e in json.loads(detail).get('errors', [])) or detail
        except (ValueError, AttributeError): nice = detail
        _record_send(False, f'HTTP {exc.code}: {nice}')
        raise RuntimeError(f'WhatsApp send failed (HTTP {exc.code})')
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        _record_send(False, 'Could not reach Telnyx: ' + type(exc).__name__)
        raise RuntimeError('WhatsApp send failed: ' + type(exc).__name__)
    _record_send(True, 'Accepted by Telnyx')
    return (data.get('data') or {}).get('id', '')

def _base_payload(settings, to):
    payload = {'from': settings.wa_from, 'to': to, 'type': 'WHATSAPP'}
    if settings.wa_profile_id: payload['messaging_profile_id'] = settings.wa_profile_id
    return payload

def send_whatsapp_text(settings, to, body):
    payload = _base_payload(settings, to)
    payload['whatsapp_message'] = {'type': 'text', 'text': {'body': body[:4000], 'preview_url': True}}
    return _telnyx_post(settings, payload)

def send_whatsapp_template(settings, to, name, lang, params):
    payload = _base_payload(settings, to)
    payload['whatsapp_message'] = {'type': 'template', 'template': {
        'name': name, 'language': {'code': lang, 'policy': 'deterministic'},
        'components': [{'type': 'body', 'parameters': [{'type': 'text', 'text': p} for p in params]}]}}
    return _telnyx_post(settings, payload)

def link_whatsapp_profile(settings):
    """Assign the WhatsApp number to the messaging profile so inbound messages reach our webhook.
    Returns (ok, message)."""
    if not (settings.telnyx_key and settings.wa_profile_id and settings.wa_from):
        return False, 'Add TELNYX_API_KEY, TELNYX_MESSAGING_PROFILE_ID and WHATSAPP_FROM_NUMBER in Render first.'
    number = normalize_phone(settings.wa_from)
    if not number: return False, 'WHATSAPP_FROM_NUMBER is not a valid international number.'
    url = 'https://api.telnyx.com/v2/whatsapp/phone_numbers/' + urllib.parse.quote(number, safe='') + '/profile'
    req = urllib.request.Request(url, data=json.dumps({'profile_id': settings.wa_profile_id}).encode(), method='PATCH',
                                 headers={'Authorization': 'Bearer ' + settings.telnyx_key,
                                          'Content-Type': 'application/json', 'Accept': 'application/json'})
    try:
        with urllib.request.urlopen(req, timeout=20) as res:
            res.read()
        return True, f'{number} is now linked to messaging profile {settings.wa_profile_id}.'
    except urllib.error.HTTPError as exc:
        detail = exc.read()[:300].decode('utf-8', 'replace')
        log.warning('WhatsApp profile link HTTP %s: %s', exc.code, detail)
        try: detail = '; '.join(e.get('detail') or e.get('title', '') for e in json.loads(detail).get('errors', [])) or detail
        except (ValueError, AttributeError): pass
        return False, f'Telnyx refused (HTTP {exc.code}): {detail[:200]}'
    except (urllib.error.URLError, TimeoutError, OSError) as exc:
        return False, 'Could not reach Telnyx: ' + type(exc).__name__

def template_safe(text: str) -> str:
    """Meta template parameters cannot contain new lines, tabs or 4+ spaces."""
    return re.sub(r'\s+', ' ', text or '').strip()[:900]

def verify_telnyx(raw: bytes, signature: str, timestamp: str, public_key: str) -> bool:
    if not public_key or not signature or not timestamp: return False
    try:
        if abs(time.time() - int(timestamp)) > 300: return False
        key = Ed25519PublicKey.from_public_bytes(base64.b64decode(public_key, validate=True))
        key.verify(base64.b64decode(signature, validate=True), timestamp.encode('ascii') + b'|' + raw)
        return True
    except (ValueError, TypeError, InvalidSignature):
        return False

def _phone_of(value):
    if isinstance(value, list): value = value[0] if value else {}
    if isinstance(value, dict): return str(value.get('phone_number') or '')
    return str(value or '')

def _text_of(payload):
    body = payload.get('body')
    if isinstance(body, dict):
        btype = str(body.get('type') or '').lower()
        text = body.get('text')
        if isinstance(text, dict) and text.get('body'): return str(text['body'])
        if isinstance(text, str) and text: return text
        inter = body.get('interactive') or {}
        for key in ('button_reply', 'list_reply'):
            if isinstance(inter.get(key), dict) and inter[key].get('title'): return str(inter[key]['title'])
        if isinstance(body.get('button'), dict) and body['button'].get('text'): return str(body['button']['text'])
        if btype:
            caption = (body.get(btype) or {}).get('caption') if isinstance(body.get(btype), dict) else ''
            return f'[{btype} received]' + (f' {caption}' if caption else '')
    elif isinstance(body, str) and body:
        return body
    return str(payload.get('text') or '')

def parse_whatsapp_event(data: dict) -> dict:
    """Normalise a Telnyx messaging webhook into one of: inbound, echo, status, ignore."""
    d = (data or {}).get('data') or {}
    event, p = d.get('event_type', ''), d.get('payload') or {}
    mtype = str(p.get('type') or '').lower()
    body = p.get('body') if isinstance(p.get('body'), dict) else {}
    if event == 'message.received':
        if mtype and mtype != 'whatsapp': return {'kind': 'ignore'}
        if str(body.get('type') or '').lower() in ('edit', 'revoke', 'reaction'): return {'kind': 'ignore'}
        frm = p.get('from') or {}
        return {'kind': 'inbound', 'phone': normalize_phone(_phone_of(frm)) or '',
                'name': str((frm.get('name') if isinstance(frm, dict) else '') or '')[:150],
                'text': _text_of(p)[:4000], 'provider_id': str(p.get('id') or body.get('foreign_id') or '')}
    if event == 'message.echo':
        return {'kind': 'echo', 'phone': normalize_phone(_phone_of(p.get('to'))) or '', 'origin': str(p.get('origin') or ''),
                'text': _text_of(p)[:4000], 'provider_id': str(p.get('id') or body.get('foreign_id') or '')}
    if event in ('message.sent', 'message.finalized', 'message.delivered', 'message.read', 'message.failed'):
        to = p.get('to')
        status = (to[0].get('status') if isinstance(to, list) and to and isinstance(to[0], dict) else '') or event.split('.')[-1]
        return {'kind': 'status', 'provider_id': str(p.get('id') or ''), 'status': str(status)[:20]}
    return {'kind': 'ignore'}

def lead_summary(lead: dict, channel: str) -> str:
    parts = [f"{FIELD_LABELS[k]}: {REQUESTS.get(lead[k], lead[k]) if k == 'request' else lead[k]}"
             for k in ORDER if k not in ('notes', 'plan_interest') and lead.get(k) not in (None, '')]
    return ('Website chat' if channel == 'web' else 'WhatsApp') + ' | ' + ' | '.join(parts)


# ---------------------------------------------------------------- AI on/off commands from WhatsApp
def chat_command(text: str):
    """Typed by the owner inside a customer's chat in the WhatsApp Business app: '#ai on' / '#ai off'.
    Returns True (on), False (off) or None (not a command)."""
    t = re.sub(r'\s+', ' ', (text or '').strip().lower())
    if t in ('#ai on', '#aion', '#ai start', '#ai'): return True
    if t in ('#ai off', '#aioff', '#ai stop'): return False
    return None

def owner_command(text: str):
    """Sent from the owner's personal WhatsApp (ADMIN_WHATSAPP_NUMBER) to the business number.
    Returns (action, target) or None. Actions: help, list, on, off. Target: '', 'all', a list number or phone digits."""
    t = re.sub(r'\s+', ' ', (text or '').strip().lower())
    m = re.fullmatch(r'ai(?: (help|list|status|on|off|start|stop)(?: (all|[+\d][\d ()+-]{0,20}))?)?', t)
    if not m: return None
    action = {'status': 'list', 'start': 'on', 'stop': 'off'}.get(m.group(1) or 'help', m.group(1) or 'help')
    target = re.sub(r'[^\dall]', '', m.group(2) or '') if (m.group(2) or '') != 'all' else 'all'
    return action, target

OWNER_HELP = ("Dialnytics AI commands (send from this number):\n"
              "AI LIST - latest WhatsApp chats with a number for each\n"
              "AI ON 3 / AI OFF 3 - switch AI for chat no. 3 in the list\n"
              "AI ON 447700900123 - or use the customer's number (last 6+ digits are enough)\n"
              "AI ON ALL / AI OFF ALL - every WhatsApp chat\n"
              "Inside a customer's chat you can also type #ai on or #ai off (the customer will see that text).")
