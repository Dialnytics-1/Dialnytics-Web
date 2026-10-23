"""Website chat widget API, Telnyx WhatsApp webhook and the admin Chats inbox."""
import json, logging, secrets, threading, time, uuid
from urllib.parse import urlencode
from collections import defaultdict
from datetime import timedelta, timezone
from fastapi import Request, HTTPException, Form, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from pydantic import BaseModel, ConfigDict, Field
from sqlalchemy import select, func, or_, delete
from sqlalchemy.exc import IntegrityError
from .database import ChatConversation, ChatMessage, Submission, MailJob
from .security import now, sha, form_token, valid_form_token
from . import chatbot as bot

log = logging.getLogger('dialnytics.chat')
MAX_AI_REPLIES = 60          # per conversation, then the team takes over
MAX_USER_MESSAGES = 150      # per website conversation
WA_DEBOUNCE_SECONDS = 1.2    # wait for a customer who sends several short messages
WINDOW = timedelta(hours=24) # WhatsApp customer-service window
LANG_NAMES = {'en': 'English', 'ur': 'Roman Urdu'}
CHANNEL_NAMES = {'web': 'Website chat', 'whatsapp': 'WhatsApp'}

class ChatStart(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    language: str = Field(max_length=4)
class ChatSend(BaseModel):
    model_config = ConfigDict(extra='forbid', str_strip_whitespace=True)
    text: str = Field(min_length=1, max_length=1000)

_locks = defaultdict(threading.Lock)
_locks_guard = threading.Lock()
def _lock(key):
    with _locks_guard: return _locks[key]

def aware(d):
    return d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d

def public_message(m):
    return {'id': m.id, 'from': {'user': 'me', 'assistant': 'bot', 'admin': 'team'}.get(m.role, 'bot'),
            'text': m.body, 'at': aware(m.created_at).isoformat() if m.created_at else ''}

def admin_message(m):
    return {'id': m.id, 'role': m.role, 'text': m.body, 'status': m.status or '',
            'at': aware(m.created_at).isoformat() if m.created_at else ''}


def register_chat(app, settings, DB, render, require_public_csrf, rate_limit, admin_session, admin_required, audit):
    """Attach chat routes. Call before the catch-all page route."""

    # ------------------------------------------------------------ helpers
    def add_message(db, conv, role, body, provider_id=None, status=''):
        msg = ChatMessage(conversation_id=conv.id, role=role, body=body or '', provider_id=provider_id or None,
                          status=status, created_at=now())
        db.add(msg)
        conv.last_message_at = now(); conv.last_preview = (body or '')[:190]
        if role == 'user':
            conv.unread = (conv.unread or 0) + 1; conv.last_inbound_at = now()
        return msg

    def lead_link(row_id): return settings.base_url + '/admin/requests/' + row_id
    def chat_link(conv_id): return settings.base_url + '/admin/chats/' + conv_id

    def apply_lead(db, conv, updates):
        """Merge collected fields; create the inbox request once required fields are complete.
        Returns a dict for the admin alert when a new lead was created."""
        lead = dict(conv.lead or {})
        lead.update({k: v for k, v in (updates or {}).items() if v not in (None, '')})
        if conv.channel == 'whatsapp' and not lead.get('whatsapp') and conv.phone: lead['whatsapp'] = conv.phone
        conv.lead = lead
        if lead.get('name'): conv.display_name = str(lead['name'])[:150]
        details = {'channel': CHANNEL_NAMES.get(conv.channel, conv.channel),
                   'calling_country': lead.get('calling_country', ''), 'users': lead.get('users', ''),
                   'plan_interest': lead.get('plan_interest', ''), 'campaign_name': lead.get('campaign_name', ''),
                   'request': bot.REQUESTS.get(lead.get('request', ''), ''), 'language': LANG_NAMES.get(conv.language, ''),
                   'conversation_id': conv.id}
        row = db.get(Submission, conv.lead_id) if conv.lead_id else None
        if row:
            row.name = str(lead.get('name') or row.name)[:150]; row.email = str(lead.get('email') or row.email or '')[:254]
            row.phone = str(lead.get('whatsapp') or row.phone)[:40]; row.company = str(lead.get('company') or row.company)[:200]
            row.message = str(lead.get('notes') or row.message or '')[:5000]
            merged = dict(row.details or {}); merged.update(details); row.details = merged
            row.updated_at = now()
            return None
        if bot.missing_fields(lead): return None
        row = Submission(id=str(uuid.uuid4()), reference='DNY-' + now().strftime('%y%m%d') + '-' + secrets.token_hex(6).upper(),
                         idempotency_key=conv.id if not db.scalar(select(Submission.id).where(Submission.idempotency_key == conv.id)) else str(uuid.uuid4()),
                         payload_hash=sha(json.dumps(lead, sort_keys=True, default=str)), kind='chat',
                         name=str(lead['name'])[:150], email=str(lead.get('email') or '')[:254],
                         phone=str(lead['whatsapp'])[:40], company=str(lead.get('company') or '')[:200],
                         subject=(bot.REQUESTS.get(lead.get('request', ''), 'Lead')) + ' - ' + CHANNEL_NAMES.get(conv.channel, 'Chat'), message=str(lead.get('notes') or '')[:5000],
                         details=details, status='new')
        db.add(row); db.flush()
        db.add(MailJob(id=str(uuid.uuid4()), submission_id=row.id))
        conv.lead_id = row.id
        return {'reference': row.reference, 'summary': bot.lead_summary(lead, conv.channel), 'link': lead_link(row.id),
                'lead': lead, 'channel': conv.channel}

    def _alert(text_lines, template_line):
        if not (settings.whatsapp_ready and settings.admin_whatsapp): return
        to = bot.normalize_phone(settings.admin_whatsapp)
        if not to: log.warning('ADMIN_WHATSAPP_NUMBER is not a valid international number'); return
        try:
            if settings.wa_alert_template:
                bot.send_whatsapp_template(settings, to, settings.wa_alert_template, settings.wa_alert_lang,
                                           [bot.template_safe(template_line)])
            else:
                bot.send_whatsapp_text(settings, to, '\n'.join(text_lines))
        except Exception as exc:
            log.warning('Admin WhatsApp alert failed: %s', exc)

    def alert_async(text_lines, template_line):
        threading.Thread(target=_alert, args=(text_lines, template_line), daemon=True).start()

    def alert_new_lead(info):
        lead = info['lead']
        lines = ['🔔 New Dialnytics lead (' + CHANNEL_NAMES.get(info['channel'], '') + ')', 'Ref: ' + info['reference']]
        lines += [f"{bot.FIELD_LABELS[k]}: {bot.REQUESTS.get(lead[k], lead[k]) if k == 'request' else lead[k]}"
                  for k in bot.ORDER if k != 'plan_interest' and lead.get(k) not in (None, '')]
        lines.append(info['link'])
        alert_async(lines, info['reference'] + ' | ' + info['summary'] + ' | ' + info['link'])

    def alert_human(conv_id, who, reason):
        alert_async(['🙋 Customer wants the team', 'From: ' + who, 'Reason: ' + reason, chat_link(conv_id)],
                    'Team needed | ' + who + ' | ' + reason + ' | ' + chat_link(conv_id))

    # ------------------------------------------------------------ AI turn
    def process_ai(conv_id, trigger_id=None, delay=0.0):
        """Generate (and on WhatsApp, send) the assistant reply. Returns new message dicts."""
        with _lock(conv_id):
            if delay: time.sleep(delay)
            with DB() as db:
                conv = db.get(ChatConversation, conv_id)
                if not conv or not conv.ai_enabled: return []
                latest = db.scalar(select(ChatMessage.id).where(ChatMessage.conversation_id == conv_id, ChatMessage.role == 'user').order_by(ChatMessage.id.desc()).limit(1))
                if not latest or (trigger_id and latest != trigger_id): return []
                last_any = db.scalar(select(ChatMessage).where(ChatMessage.conversation_id == conv_id).order_by(ChatMessage.id.desc()).limit(1))
                if last_any and last_any.role != 'user': return []   # already answered
                rows = [(r.role, r.body) for r in db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conv_id).order_by(ChatMessage.id.desc()).limit(40)).all()][::-1]
                language, lead, channel, ai_count = conv.language, dict(conv.lead or {}), conv.channel, conv.ai_replies or 0
                phone, who = conv.phone, conv.display_name or conv.phone or 'Website visitor'
            last_text = next((b for r, b in reversed(rows) if r == 'user'), '')
            replies, result, disable_ai, human_reason = [], bot.AIResult(), False, ''
            # No language menu: the assistant mirrors the customer's own style (English / Roman Urdu mix).
            language = bot.guess_language(last_text)
            if not replies:
                if ai_count >= MAX_AI_REPLIES:
                    replies = [bot.LIMIT_REACHED[language]]; disable_ai = True; human_reason = 'AI reply limit reached'
                elif not settings.ai_ready:
                    replies = [bot.PAUSED_NOTE[language]]; disable_ai = True; human_reason = 'AI is not configured (ANTHROPIC_API_KEY missing)'
                else:
                    result = bot.run_ai(settings, rows, language, channel, lead, settings.base_url)
                    if result.text: replies = [result.text]
                    if result.human: human_reason = result.human
                    if result.error: human_reason = human_reason or 'AI temporarily unavailable'
            # The admin may have switched AI off while the reply was being written.
            with DB() as db:
                conv = db.get(ChatConversation, conv_id)
                if not conv or not conv.ai_enabled: return []
            sent = []
            for text in replies:
                pid, status = None, ''
                if channel == 'whatsapp':
                    try: pid, status = bot.send_whatsapp_text(settings, phone, text) or None, 'sent'
                    except Exception as exc:
                        log.warning('AI WhatsApp reply failed: %s', exc); status = 'failed'
                sent.append((text, pid, status))
            new_lead = None
            with DB.begin() as db:
                conv = db.get(ChatConversation, conv_id)
                if not conv: return []
                if language: conv.language = language
                if result.lead_updates or (channel == 'whatsapp' and not (conv.lead or {}).get('whatsapp')):
                    new_lead = apply_lead(db, conv, result.lead_updates)
                notify_human = bool(human_reason) and not conv.needs_human
                if human_reason: conv.needs_human = True
                if disable_ai: conv.ai_enabled = False
                msgs = [add_message(db, conv, 'assistant', t, p, s) for t, p, s in sent]
                conv.ai_replies = (conv.ai_replies or 0) + sum(1 for t, p, s in sent if t not in (bot.LANG_MENU,))
                db.flush()
                out = [public_message(m) for m in msgs]
            if new_lead: alert_new_lead(new_lead)
            if notify_human: alert_human(conv_id, who, human_reason)
            return out

    # ------------------------------------------------------------ website widget API
    def web_key(request):
        token = request.cookies.get('mkt_chat', '')
        return ('web:' + sha(token)) if len(token) >= 32 else None

    def web_conversation(db, request):
        key = web_key(request)
        return db.scalar(select(ChatConversation).where(ChatConversation.contact_key == key)) if key else None

    @app.get('/api/chat/history')
    def chat_history(request: Request, after: int = 0):
        csrf = request.cookies.get('mkt_form')
        if not valid_form_token(settings.secret, csrf, 'public'): csrf = form_token(settings.secret, 'public')
        payload = {'enabled': settings.chat_enabled, 'csrf': csrf, 'language': '', 'ai': True, 'messages': []}
        with DB() as db:
            conv = web_conversation(db, request)
            if conv:
                payload.update(language=conv.language, ai=bool(conv.ai_enabled))
                payload['messages'] = [public_message(m) for m in db.scalars(select(ChatMessage).where(
                    ChatMessage.conversation_id == conv.id, ChatMessage.id > max(0, after), ChatMessage.role != 'system'
                ).order_by(ChatMessage.id).limit(200)).all()]
        res = JSONResponse(payload)
        res.set_cookie('mkt_form', csrf, max_age=7200, httponly=True, secure=settings.production, samesite='lax')
        return res

    @app.post('/api/chat/start')
    def chat_start(request: Request, data: ChatStart):
        require_public_csrf(request)
        if not settings.chat_enabled: raise HTTPException(404, 'Chat is not available.')
        if data.language not in ('en', 'ur'): raise HTTPException(422, 'Choose English or Roman Urdu.')
        new_cookie = None
        with DB() as db:
            exists = web_conversation(db, request) is not None
        if not exists: rate_limit(request, 'chatnew', 10, 3600)
        with DB.begin() as db:
            conv = web_conversation(db, request)
            if not conv:
                token = secrets.token_urlsafe(32); new_cookie = token
                conv = ChatConversation(id=str(uuid.uuid4()), channel='web', contact_key='web:' + sha(token),
                                        language=data.language, ai_enabled=True, lead={}, created_at=now(), last_message_at=now())
                db.add(conv); db.flush()
                msgs = [add_message(db, conv, 'assistant', bot.GREETING[data.language])]
            else:
                msgs = []
                if conv.language != data.language:
                    conv.language = data.language
                    msgs = [add_message(db, conv, 'assistant', bot.GREETING[data.language])]
            db.flush()
            out = {'language': conv.language, 'ai': bool(conv.ai_enabled), 'messages': [public_message(m) for m in msgs]}
        res = JSONResponse(out)
        if new_cookie:
            res.set_cookie('mkt_chat', new_cookie, max_age=60 * 60 * 24 * 30, httponly=True, secure=settings.production, samesite='lax')
        return res

    @app.post('/api/chat/message')
    def chat_message(request: Request, data: ChatSend):
        require_public_csrf(request)
        if not settings.chat_enabled: raise HTTPException(404, 'Chat is not available.')
        rate_limit(request, 'chat', 40, 3600)
        with DB() as db:
            exists = web_conversation(db, request) is not None
        if not exists: rate_limit(request, 'chatnew', 10, 3600)
        new_cookie = None
        with DB.begin() as db:
            conv = web_conversation(db, request)
            if not conv:
                new_cookie = secrets.token_urlsafe(32)
                conv = ChatConversation(id=str(uuid.uuid4()), channel='web', contact_key='web:' + sha(new_cookie),
                                        language='', ai_enabled=True, lead={}, created_at=now(), last_message_at=now())
                db.add(conv); db.flush()
            count = db.scalar(select(func.count()).select_from(ChatMessage).where(ChatMessage.conversation_id == conv.id, ChatMessage.role == 'user'))
            if count >= MAX_USER_MESSAGES: raise HTTPException(429, 'This chat is very long. Please continue with us on WhatsApp.')
            msg = add_message(db, conv, 'user', data.text)
            db.flush()
            conv_id, msg_id, ai_on = conv.id, msg.id, bool(conv.ai_enabled)
            mine = public_message(msg)
        replies = process_ai(conv_id, msg_id) if ai_on else []
        res = JSONResponse({'messages': [mine] + replies, 'ai': ai_on, 'waiting': not ai_on})
        if new_cookie:
            res.set_cookie('mkt_chat', new_cookie, max_age=60 * 60 * 24 * 30, httponly=True, secure=settings.production, samesite='lax')
        return res

    # ------------------------------------------------------------ WhatsApp webhook (Telnyx)
    @app.post('/webhooks/telnyx/whatsapp')
    async def whatsapp_webhook(request: Request, background: BackgroundTasks):
        raw = await request.body()
        if not settings.telnyx_public_key: return JSONResponse({'detail': 'WhatsApp is not configured.'}, status_code=503)
        if not bot.verify_telnyx(raw, request.headers.get('telnyx-signature-ed25519', ''), request.headers.get('telnyx-timestamp', ''), settings.telnyx_public_key):
            return JSONResponse({'detail': 'Invalid signature.'}, status_code=401)
        try: event = bot.parse_whatsapp_event(json.loads(raw.decode('utf-8')))
        except (ValueError, UnicodeDecodeError): return JSONResponse({'detail': 'Invalid JSON.'}, status_code=400)
        own = bot.normalize_phone(settings.wa_from)
        kind = event['kind']
        if kind in ('inbound', 'echo') and event.get('phone') and event['phone'] != own:
            if kind == 'echo' and event.get('origin') not in (None, '', 'whatsapp_business_app'):
                return {'ok': True}
            job = None
            try:
                with DB.begin() as db:
                    if event['provider_id'] and db.scalar(select(ChatMessage.id).where(ChatMessage.provider_id == event['provider_id'])):
                        return {'ok': True, 'duplicate': True}
                    key = 'wa:' + event['phone']
                    conv = db.scalar(select(ChatConversation).where(ChatConversation.contact_key == key))
                    if not conv:
                        conv = ChatConversation(id=str(uuid.uuid4()), channel='whatsapp', contact_key=key, phone=event['phone'],
                                                display_name=event.get('name', ''), ai_enabled=settings.wa_ai_default,
                                                lead={'whatsapp': event['phone']}, created_at=now(), last_message_at=now())
                        db.add(conv); db.flush()
                    elif event.get('name') and not conv.display_name:
                        conv.display_name = event['name']
                    if kind == 'inbound':
                        msg = add_message(db, conv, 'user', event['text'] or '[empty message]', event['provider_id'])
                        db.flush()
                        if conv.ai_enabled: job = (conv.id, msg.id)
                    else:
                        # Owner replied from the WhatsApp Business app: stop the AI for this chat.
                        add_message(db, conv, 'admin', event['text'], event['provider_id'], 'sent')
                        conv.ai_enabled = False; conv.needs_human = False; conv.unread = 0
            except IntegrityError:
                return {'ok': True, 'duplicate': True}
            if job: background.add_task(process_ai, job[0], job[1], WA_DEBOUNCE_SECONDS)
        elif kind == 'status' and event.get('provider_id'):
            with DB.begin() as db:
                m = db.scalar(select(ChatMessage).where(ChatMessage.provider_id == event['provider_id']))
                if m: m.status = event['status']
        return {'ok': True}

    # ------------------------------------------------------------ admin Chats inbox
    def conv_or_404(db, conv_id):
        conv = db.get(ChatConversation, conv_id)
        if not conv: raise HTTPException(404, 'Chat not found.')
        return conv

    def window_open(conv):
        return bool(conv.last_inbound_at and aware(conv.last_inbound_at) > now() - WINDOW)

    @app.get('/admin/chats', response_class=HTMLResponse)
    def chats(request: Request, channel: str = '', view: str = '', q: str = ''):
        sess = admin_session(request)
        if not sess: return RedirectResponse('/admin/login', status_code=303)
        qry = select(ChatConversation)
        if channel in ('web', 'whatsapp'): qry = qry.where(ChatConversation.channel == channel)
        if view == 'human': qry = qry.where(ChatConversation.needs_human.is_(True))
        elif view == 'ai_off': qry = qry.where(ChatConversation.ai_enabled.is_(False))
        elif view == 'ai_on': qry = qry.where(ChatConversation.ai_enabled.is_(True))
        elif view == 'unread': qry = qry.where(ChatConversation.unread > 0)
        elif view == 'leads': qry = qry.where(ChatConversation.lead_id.is_not(None))
        if q:
            term = q.strip()[:100]
            qry = qry.where(or_(ChatConversation.display_name.icontains(term, autoescape=True), ChatConversation.phone.icontains(term, autoescape=True), ChatConversation.last_preview.icontains(term, autoescape=True)))
        with DB() as db:
            rows = db.scalars(qry.order_by(ChatConversation.last_message_at.desc()).limit(200)).all()
            stats = {
                'total': db.scalar(select(func.count()).select_from(ChatConversation)),
                'unread': db.scalar(select(func.count()).select_from(ChatConversation).where(ChatConversation.unread > 0)),
                'human': db.scalar(select(func.count()).select_from(ChatConversation).where(ChatConversation.needs_human.is_(True))),
                'ai_on': db.scalar(select(func.count()).select_from(ChatConversation).where(ChatConversation.ai_enabled.is_(True))),
                'leads': db.scalar(select(func.count()).select_from(ChatConversation).where(ChatConversation.lead_id.is_not(None))),
            }
        return render(request, 'admin_chats.html', {'page_title': 'Chats', 'admin': sess, 'rows': rows, 'stats': stats,
                      'channel': channel, 'view': view, 'q': q, 'mail_ready': settings.mail_ready,
                      'ai_ready': settings.ai_ready, 'whatsapp_ready': settings.whatsapp_ready,
                      'alerts_ready': bool(settings.whatsapp_ready and settings.admin_whatsapp),
                      'profile_ready': bool(settings.telnyx_key and settings.wa_profile_id)})

    @app.get('/admin/chats/badge.json')
    def chats_badge(request: Request):
        if not admin_session(request): raise HTTPException(401, 'Admin login required.')
        with DB() as db:
            unread = db.scalar(select(func.count()).select_from(ChatConversation).where(or_(ChatConversation.unread > 0, ChatConversation.needs_human.is_(True))))
        return {'unread': unread}

    @app.post('/admin/whatsapp/link')
    def whatsapp_link(request: Request, csrf: str = Form(...)):
        sess = admin_required(request, csrf)
        ok, message = bot.link_whatsapp_profile(settings)
        with DB.begin() as db: audit(db, sess, 'WhatsApp profile link: ' + ('ok' if ok else 'failed'))
        return RedirectResponse('/admin/chats?' + urlencode({'link': 'ok' if ok else 'fail', 'msg': message[:250]}), status_code=303)

    @app.get('/admin/chats/{conv_id}', response_class=HTMLResponse)
    def chat_detail(request: Request, conv_id: str):
        sess = admin_session(request)
        if not sess: return RedirectResponse('/admin/login', status_code=303)
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id)
            conv.unread = 0
            messages = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conv_id).order_by(ChatMessage.id.desc()).limit(300)).all()[::-1]
            lead_row = db.get(Submission, conv.lead_id) if conv.lead_id else None
            lead_ref = lead_row.reference if lead_row else ''
        lead = dict(conv.lead or {})
        fields = [(bot.FIELD_LABELS[k], bot.REQUESTS.get(lead.get(k, ''), lead.get(k, '')) if k == 'request' else lead.get(k, '')) for k in bot.ORDER]
        return render(request, 'admin_chat_detail.html', {'page_title': conv.display_name or conv.phone or 'Website visitor', 'admin': sess,
                      'conv': conv, 'messages': messages, 'fields': fields, 'missing': [bot.FIELD_LABELS[f] for f in bot.missing_fields(lead)],
                      'lead_ref': lead_ref, 'lang_name': LANG_NAMES.get(conv.language, 'Not chosen yet'),
                      'channel_name': CHANNEL_NAMES.get(conv.channel, conv.channel), 'window_open': window_open(conv),
                      'last_id': messages[-1].id if messages else 0, 'mail_ready': settings.mail_ready,
                      'whatsapp_ready': settings.whatsapp_ready, 'ai_ready': settings.ai_ready,
                      'error': request.query_params.get('error', ''), 'saved': request.query_params.get('saved', '')})

    @app.get('/admin/chats/{conv_id}/poll')
    def chat_poll(request: Request, conv_id: str, after: int = 0):
        if not admin_session(request): raise HTTPException(401, 'Admin login required.')
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id)
            msgs = db.scalars(select(ChatMessage).where(ChatMessage.conversation_id == conv_id, ChatMessage.id > max(0, after)).order_by(ChatMessage.id).limit(100)).all()
            if msgs: conv.unread = 0
            return {'messages': [admin_message(m) for m in msgs], 'ai_enabled': bool(conv.ai_enabled),
                    'needs_human': bool(conv.needs_human), 'window_open': window_open(conv)}

    @app.post('/admin/chats/{conv_id}/ai')
    def chat_toggle(request: Request, background: BackgroundTasks, conv_id: str, csrf: str = Form(...), enabled: str = Form(...)):
        sess = admin_required(request, csrf)
        on = enabled == '1'
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id)
            conv.ai_enabled = on
            if on: conv.needs_human = False
            audit(db, sess, ('AI on' if on else 'AI off') + ' for chat ' + (conv.phone or conv.display_name or 'web')[:40])
            last = db.scalar(select(ChatMessage).where(ChatMessage.conversation_id == conv_id).order_by(ChatMessage.id.desc()).limit(1))
            pending = on and last is not None and last.role == 'user'
        if pending:
            # Answer the customer's waiting message now that AI is back on.
            background.add_task(process_ai, conv_id, None, 0.0)
        return RedirectResponse('/admin/chats/' + conv_id + '?saved=ai', status_code=303)

    @app.post('/admin/chats/{conv_id}/reply')
    def chat_reply(request: Request, conv_id: str, csrf: str = Form(...), body: str = Form(...)):
        sess = admin_required(request, csrf)
        text = body.strip()
        if not text or len(text) > 4000: raise HTTPException(422, 'Write a reply of up to 4000 characters.')
        with DB() as db:
            conv = conv_or_404(db, conv_id)
            channel, phone, open_window = conv.channel, conv.phone, window_open(conv)
        pid, status = None, ''
        if channel == 'whatsapp':
            if not settings.whatsapp_ready: return RedirectResponse('/admin/chats/' + conv_id + '?error=setup', status_code=303)
            if not open_window: return RedirectResponse('/admin/chats/' + conv_id + '?error=window', status_code=303)
            try: pid, status = bot.send_whatsapp_text(settings, phone, text) or None, 'sent'
            except Exception: return RedirectResponse('/admin/chats/' + conv_id + '?error=send', status_code=303)
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id)
            add_message(db, conv, 'admin', text, pid, status)
            conv.ai_enabled = False; conv.needs_human = False; conv.unread = 0
            audit(db, sess, 'manual chat reply (AI stopped)')
        return RedirectResponse('/admin/chats/' + conv_id + '?saved=reply', status_code=303)

    @app.post('/admin/chats/{conv_id}/resolve')
    def chat_resolve(request: Request, conv_id: str, csrf: str = Form(...)):
        sess = admin_required(request, csrf)
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id); conv.needs_human = False; conv.unread = 0
            audit(db, sess, 'chat marked handled')
        return RedirectResponse('/admin/chats/' + conv_id + '?saved=resolved', status_code=303)

    @app.post('/admin/chats/{conv_id}/delete')
    def chat_delete(request: Request, conv_id: str, csrf: str = Form(...)):
        sess = admin_required(request, csrf)
        with DB.begin() as db:
            conv = conv_or_404(db, conv_id)
            db.execute(delete(ChatMessage).where(ChatMessage.conversation_id == conv_id))
            db.delete(conv)
            audit(db, sess, 'chat deleted')
        return RedirectResponse('/admin/chats?deleted=1', status_code=303)

    app.state.process_ai = process_ai
