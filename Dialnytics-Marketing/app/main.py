"""Independent Dialnytics marketing app. Contains no telephony credentials or dialer writes."""
import asyncio, contextlib, csv, io, json, logging, secrets, uuid, math, time, hmac, os
from datetime import datetime, timedelta, timezone, date
from urllib.parse import urlencode, urlparse
from contextlib import asynccontextmanager
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException, Form
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import BaseModel, EmailStr, Field, ConfigDict, field_validator
from sqlalchemy import select, update, delete, func, or_, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from .settings import Settings, ROOT
from .database import make_database, init_database, Submission, AdminSession, Note, MailJob, Audit, RateBucket, Setting, PhoneInventory
from .security import now, sha, verify_password, form_token, valid_form_token, csv_safe
from .catalog import BUSINESS, PLANS, FEATURES, EUROPE_COUNTRIES, price_quote, client_catalog, addon_view, PRICE_FIELDS, DEFAULT_PRICES, PRICES, clean_prices, apply_prices, price_view, usd
from .content import PAGES, COLLECTIONS, PRODUCT_LINKS, SOLUTION_LINKS, FAQ, BLOG_POSTS, refresh_price_text
from .mail import deliver_one
from .chat_routes import register_chat
from .payments import checkout_params, create_checkout, verify_webhook
from .tools import TOOLS, TOOL_MAP

log=logging.getLogger('dialnytics.marketing')
STATUSES=['new','contacted','awaiting_payment','paid','demo_confirmed','closed','spam']
KINDS=['order','contact','demo','quote','support']
ADMIN_KINDS=KINDS+['chat','newsletter']  # 'chat' leads come from the AI assistant; 'newsletter' from the footer signup

class RequestData(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    kind: str
    name: str=Field(min_length=2,max_length=150)
    email: EmailStr
    phone: str=Field(default='',max_length=40)
    company: str=Field(default='',max_length=200)
    subject: str=Field(default='',max_length=180)
    message: str=Field(default='',max_length=5000)
    plan: str=Field(default='',max_length=40)
    users: int=Field(default=1,ge=1,le=100,strict=True)
    countries: list[str]=Field(default_factory=list,max_length=6)
    addons: list[str]=Field(default_factory=list,max_length=4)
    payment: str=Field(default='',max_length=30)
    number_preference: str=Field(default='',max_length=200)
    number_country: str=Field(default='',max_length=2)
    number_ids: list[str]=Field(default_factory=list,max_length=100)
    dialer_password: str=Field(default='',max_length=128)
    preferred_date: str=Field(default='',max_length=40)
    preferred_time: str=Field(default='',max_length=40)
    timezone: str=Field(default='Asia/Karachi',max_length=80)
    consent: bool
    website: str=Field(default='',max_length=200)  # honeypot
    idempotency_key: uuid.UUID
    @field_validator('kind')
    @classmethod
    def kind_allowed(cls,value):
        if value not in KINDS: raise ValueError('Choose a valid request type.')
        return value
    @field_validator('name','subject','company','phone','number_preference')
    @classmethod
    def no_controls(cls,v):
        if any(ord(c)<32 for c in v): raise ValueError('Use plain text without control characters.')
        return v

class NewsletterData(BaseModel):
    model_config=ConfigDict(extra='forbid',str_strip_whitespace=True)
    email: EmailStr
    consent: bool
    website: str=Field(default='',max_length=200)  # honeypot
    idempotency_key: uuid.UUID

def aware(d): return d.replace(tzinfo=timezone.utc) if d and d.tzinfo is None else d

class BodyLimit:
    def __init__(self, app, limit=65536): self.app,self.limit=app,limit
    async def __call__(self, scope, receive, send):
        if scope['type']!='http' or scope.get('method') not in ('POST','PUT','PATCH'):
            return await self.app(scope,receive,send)
        chunks=[]; size=0
        while True:
            message=await receive()
            if message['type']=='http.disconnect': return
            data=message.get('body',b'');size+=len(data)
            if size>self.limit:
                return await JSONResponse({'detail':'Request exceeds 64 KB.'},status_code=413)(scope,receive,send)
            chunks.append(data)
            if not message.get('more_body',False): break
        replayed=False
        async def replay():
            nonlocal replayed
            if not replayed:
                replayed=True
                return {'type':'http.request','body':b''.join(chunks),'more_body':False}
            return await receive()
        return await self.app(scope,replay,send)

def create_app(settings=None):
    settings=settings or Settings()
    (ROOT/'data').mkdir(exist_ok=True)
    engine,DB=make_database(settings.database_url)
    templates=Jinja2Templates(directory=str(ROOT/'templates'))
    templates.env.filters['money']=lambda x: f'{float(x):,.2f}' if x is not None else 'Quote'
    templates.env.filters['stamp']=lambda x: aware(x).astimezone(timezone(timedelta(hours=5))).strftime('%d %b %Y, %I:%M %p PKT') if x else '-'
    templates.env.filters['pretty']=lambda x: json.dumps(x,indent=2,ensure_ascii=False)
    templates.env.filters['usd']=lambda x: usd(x) if x is not None else ''

    # Admin-managed prices live in the marketing database (mkt_settings, key 'prices').
    price_state={'checked':0.0,'stamp':None}
    def load_prices(force=False):
        if not force and time.monotonic()-price_state['checked']<30: return
        price_state['checked']=time.monotonic()
        with DB() as db: row=db.get(Setting,'prices')
        stamp=(row.updated_at.isoformat() if row and row.updated_at else None)
        if not force and stamp==price_state['stamp']: return
        values=(row.value or {}).get('values',{}) if row else {}
        try: apply_prices(clean_prices({**{k:str(v) for k,v in DEFAULT_PRICES.items()},**values}) if values else {}, (row.value or {}).get('version') if row else None)
        except ValueError: log.error('Stored prices are invalid; using defaults.'); apply_prices({})
        refresh_price_text(); price_state['stamp']=stamp

    @asynccontextmanager
    async def lifespan(app):
        settings.validate()
        init_database(engine)
        try: load_prices(force=True)
        except SQLAlchemyError: log.exception('Could not load saved prices; using defaults.')
        stop=asyncio.Event()
        async def mail_loop():
            while not stop.is_set():
                try: await asyncio.to_thread(deliver_one,DB,settings)
                except Exception: log.exception('Marketing mail worker error')
                try: await asyncio.wait_for(stop.wait(),timeout=15)
                except asyncio.TimeoutError: pass
        task=asyncio.create_task(mail_loop()) if settings.worker else None
        yield
        stop.set()
        if task: await task
        engine.dispose()
    app=FastAPI(title='Dialnytics Marketing',lifespan=lifespan,docs_url=None,redoc_url=None,openapi_url=None)
    app.state.settings=settings; app.state.DB=DB; app.state.engine=engine
    app.add_middleware(BodyLimit)
    app.mount('/static',StaticFiles(directory=str(ROOT/'static')),name='static')

    @app.middleware('http')
    async def security_headers(request, call_next):
        if request.method in ('POST', 'PUT', 'PATCH', 'DELETE'):
            origin = request.headers.get('origin')

            allowed_origins = {
                'https://dialnytics.uk',
                'https://www.dialnytics.uk',
                'https://dialnytics.com',
                'https://www.dialnytics.com',
            }

            if not settings.production:
                allowed_origins.add(str(request.base_url).rstrip('/'))

            if origin and origin.rstrip('/') not in allowed_origins:
                return JSONResponse(
                    {'detail': 'Cross-origin request refused.'},
                    status_code=403
                )

        try: load_prices()
        except SQLAlchemyError: log.warning('Price refresh skipped: database unavailable.')
        response = await call_next(request)

        response.headers['X-Content-Type-Options'] = 'nosniff'
        framable = request.url.path.startswith('/static/product-tour/')
        response.headers['X-Frame-Options'] = 'SAMEORIGIN' if framable else 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=()'
        )
        

        response.headers['Content-Security-Policy'] = (
            "default-src 'self'; "
            "script-src 'self' https://connect.facebook.net https://www.googletagmanager.com; "
            "style-src 'self' 'unsafe-inline'; "
            "img-src 'self' data: https://www.facebook.com https://www.google-analytics.com https://region1.google-analytics.com; "
            "font-src 'self'; "
            "connect-src 'self' https://www.facebook.com https://connect.facebook.net https://www.google-analytics.com https://region1.google-analytics.com https://*.google-analytics.com; "
            "form-action 'self'; "
            "frame-ancestors " + ("'self'" if framable else "'none'") + "; "
            "base-uri 'self'; "
            "object-src 'none'"
        )




        if request.url.path.startswith(('/admin', '/api')):
            response.headers['Cache-Control'] = 'no-store'
            response.headers['X-Robots-Tag'] = 'noindex, nofollow'

        if settings.production:
            response.headers['Strict-Transport-Security'] = 'max-age=31536000'

        return response

    @app.exception_handler(SQLAlchemyError)
    async def database_error(request, exc):
        log.error('Marketing database operation failed: %s', type(exc).__name__)
        return JSONResponse({'detail': 'The service is temporarily unavailable. We could not confirm this operation. Please retry or contact the team.'}, status_code=503)

    def render(request,name,context=None,status=200):
        csrf=request.cookies.get('mkt_form')
        if not valid_form_token(settings.secret,csrf,'public'): csrf=form_token(settings.secret,'public')
        ctx={'business':BUSINESS,'plans':PLANS,'features':FEATURES,'faq':FAQ,
             'product_links':PRODUCT_LINKS,'solution_links':SOLUTION_LINKS,
             'catalog':client_catalog(),'pricing':price_view(),'addons':addon_view(),'csrf':csrf,'year':now().year,
             'base_url':settings.base_url,'canonical':settings.base_url+request.url.path,
             'current_path':request.url.path,'chat_enabled':settings.chat_enabled,'card_checkout':settings.stripe_ready,'signup_enabled':bool(os.getenv('DIALNYTICS_SIGNUP_FERNET_KEY')),'page_title':'Business calling, without the extra layers.',
             'description':'Unlimited business calling, dedicated caller ID, CRM, Power Dialer and recording. Clear prices. A human setup process.',
             **(context or {})}
        response=templates.TemplateResponse(request=request,name=name,context=ctx,status_code=status)
        response.set_cookie('mkt_form',csrf,max_age=7200,httponly=True,secure=settings.production,samesite='lax')
        return response

    def require_public_csrf(request):
        supplied=request.headers.get('X-CSRF-Token','')
        cookie=request.cookies.get('mkt_form','')
        if not supplied or not hmac.compare_digest(supplied,cookie) or not valid_form_token(settings.secret,supplied,'public'):
            raise HTTPException(403,'Your form session expired. Refresh the page and try again.')

    def rate_limit(request,prefix,limit,seconds):
        # IPs are keyed hashes, not stored in the public request records.
        ip=request.client.host if request.client else 'unknown'
        bucket=int(time.time())//seconds
        key=prefix+':'+sha(settings.secret+ip)+':'+str(bucket)
        with DB.begin() as db:
            result=db.execute(update(RateBucket).where(RateBucket.key==key,RateBucket.count<limit).values(count=RateBucket.count+1))
            if result.rowcount: return
            exists=db.get(RateBucket,key)
            if exists: raise HTTPException(429,'Too many attempts. Please try again later.',headers={'Retry-After':str(seconds)})
            try:
                with db.begin_nested(): db.add(RateBucket(key=key,count=1,expires_at=now()+timedelta(seconds=seconds*2))); db.flush()
            except IntegrityError:
                result=db.execute(update(RateBucket).where(RateBucket.key==key,RateBucket.count<limit).values(count=RateBucket.count+1))
                if not result.rowcount: raise HTTPException(429,'Too many attempts. Please try again later.')
            db.execute(delete(RateBucket).where(RateBucket.expires_at<now()))

    def admin_session(request):
        raw=request.cookies.get('mkt_admin','')
        if not raw: return None
        with DB() as db:
            sess=db.get(AdminSession,sha(raw))
            if sess and aware(sess.expires_at)>now() and sess.credential_tag==sha(settings.admin_password_hash) and sess.email==settings.admin_email:
                return sess
        return None
    def admin_required(request,csrf=None):
        sess=admin_session(request)
        if not sess: raise HTTPException(401,'Admin login required.')
        if csrf is not None and not hmac.compare_digest(sess.csrf,csrf): raise HTTPException(403,'Invalid form token. Reload the admin page.')
        return sess
    def audit(db,sess,action,reference=''): db.add(Audit(actor=sess.email,action=action,reference=reference))

    @app.get('/healthz')
    def health():
        try:
            with engine.connect() as conn: conn.execute(text('SELECT 1'))
        except SQLAlchemyError: return JSONResponse({'status':'unavailable'},status_code=503)
        return {'status':'ok','application':'dialnytics-marketing'}
    @app.get('/favicon.ico')
    def favicon(): return RedirectResponse('/static/img/favicon.svg',status_code=302)
    @app.get('/',response_class=HTMLResponse)
    def home(request:Request): return render(request,'home.html',{'blog_posts':BLOG_POSTS,'page_title':'Business calling for teams that sell abroad','description':'Local US, UK, Australian and Japanese business numbers in your browser. Unlimited calling in your plan countries, CRM and voicemail included. From one clear per-user price, taxes included.'})
    @app.get('/pricing/',response_class=HTMLResponse)
    def pricing(request:Request): return render(request,'pricing.html',{'page_title':'One plan price. Add only what you need.'})
    @app.get('/get-started/',response_class=HTMLResponse)
    def get_started(request:Request): return RedirectResponse('/pricing/#plans',status_code=303)
    @app.get('/get-started/{plan}/',response_class=HTMLResponse)
    def order(request:Request,plan:str):
        if plan=='team': return RedirectResponse('/get-started/usa-canada/?users=3',status_code=303)
        if plan in ('usa','canada'): plan='usa-canada'
        if plan not in PLANS: raise HTTPException(404,'Plan not found.')
        return render(request,'order.html',{'plan_slug':plan,'plan':PLANS[plan],'page_title':'Build your '+PLANS[plan]['name']+' plan'})
    @app.get('/numbers/',response_class=HTMLResponse)
    def numbers(request:Request): return render(request,'countries.html',{'page_title':'Where will your next conversation go?'})
    @app.get('/numbers/{country}/',response_class=HTMLResponse)
    def country(request:Request,country:str):
        plan='usa-canada' if country in ('usa','canada') else country
        if plan not in PLANS: raise HTTPException(404,'Country plan not found.')
        title={'usa':'USA','canada':'Canada'}.get(country,PLANS[plan]['name'])
        return render(request,'country.html',{'plan_slug':plan,'plan':PLANS[plan],'country_name':title,'page_title':title+' business calling'})
    @app.get('/tools/',response_class=HTMLResponse)
    def tools_hub(request:Request): return render(request,'tools.html',{'page_title':'Free tools for calling teams','description':'Free browser tools: best time to call, A2P 10DLC quiz, follow-up planner, number cleaner, staffing calculator, area codes, SMS counter and call scripts.','tools':TOOLS})
    @app.get('/tools/{slug}/',response_class=HTMLResponse)
    def tool_page(request:Request,slug:str):
        if slug not in TOOL_MAP: raise HTTPException(404,'Tool not found.')
        t=TOOL_MAP[slug]
        return render(request,'tool.html',{'page_title':t[1],'description':t[2],'tool':t,'tools':TOOLS})
    @app.get('/product/tour/',response_class=HTMLResponse)
    def tour(request:Request): return render(request,'tour.html',{'page_title':'A closer look at your calling workflow.'})
    @app.get('/faq/',response_class=HTMLResponse)
    def faq_page(request:Request): return render(request,'faq.html',{'page_title':'A few answers before your next call.'})
    @app.get('/book-demo/',response_class=HTMLResponse)
    def demo(request:Request): return render(request,'form.html',{'kind':'demo','page_title':'Book a demo or ask for a trial.','form_title':'Request a demo or trial','description':'Tell us what your team needs. We will message you on WhatsApp to confirm a 15-minute demo. Short trials are offered case by case after we review your business.'})
    @app.get('/contact/',response_class=HTMLResponse)
    def contact(request:Request): return render(request,'form.html',{'kind':'contact','page_title':"Let's talk about your next step.",'form_title':'Send us a message'})
    @app.get('/support/',response_class=HTMLResponse)
    def support(request:Request): return render(request,'form.html',{'kind':'support','page_title':'A human team, when you need help.','form_title':'Contact support','description':BUSINESS['support_hours']+'. Activation is available 24/7, separately from support hours.'})
    @app.get('/custom-quote/',response_class=HTMLResponse)
    def quote_page(request:Request): return render(request,'form.html',{'kind':'quote','page_title':'A plan built around your destinations.','form_title':'Request a custom quote'})
    @app.get('/trial-and-demo/')
    def old_demo(): return RedirectResponse('/book-demo/',status_code=301)
    @app.get('/roadmap/')
    def old_roadmap(): return RedirectResponse('/product/',status_code=301)
    @app.get('/request-trial/')
    def no_trial(): return RedirectResponse('/book-demo/',status_code=301)
    @app.get('/search/',response_class=HTMLResponse)
    def search(request:Request,q:str=''):
        q=q.strip()[:150]
        results=[p for p in PAGES.values() if q and q.lower() in (p['title']+' '+p['description']+' '+p.get('label','')).lower()]
        return render(request,'search.html',{'q':q,'results':results[:60],'page_title':'Search Dialnytics guides'})

    @app.post('/api/quote')
    def calculate(request:Request,data:dict):
        require_public_csrf(request)
        try: return price_quote(data.get('plan'),data.get('users'),data.get('countries',[]),data.get('addons',[]))
        except (ValueError,TypeError): raise HTTPException(422,'Choose a valid plan, user count and destination selection.')

    @app.post('/api/requests')
    def submit(request:Request,data:RequestData):
        require_public_csrf(request)
        if data.website: raise HTTPException(400,'Unable to submit this request.')
        if not data.consent: raise HTTPException(422,'Please acknowledge the privacy notice and request terms.')
        if data.kind in ('order','demo'):
            import re
            if not re.fullmatch(r'\+[1-9][0-9\s()-]{6,24}',data.phone):
                raise HTTPException(422,'Enter a WhatsApp number with country code, for example +44 7700 900123.')
        if data.kind in ('contact','support','quote') and len(data.message)<10:
            raise HTTPException(422,'Please include at least 10 characters in your message.')
        details={}
        if data.kind=='order':
            if data.dialer_password:
                if not os.getenv('DIALNYTICS_SIGNUP_FERNET_KEY'):
                    raise HTTPException(503,'Self-service registration is not configured.')
                if len(data.dialer_password)<12:
                    raise HTTPException(422,'Choose a password of at least 12 characters.')
            try: details=price_quote(data.plan,data.users,data.countries,data.addons)
            except ValueError as exc: raise HTTPException(422,str(exc))
            if data.payment not in ('bank','usdt','stripe'): raise HTTPException(422,'Choose a payment preference.')
            details.update(payment=data.payment,number_preference=data.number_preference)
            if data.number_ids or data.number_country:
                if os.getenv('DIALNYTICS_REQUIRE_OWNED_NUMBERS') != '1':
                    raise HTTPException(422,'Owned number checkout is not enabled.')
                from .checkout_inventory import validate_number_choice
                try:
                    validate_number_choice(data.number_country, data.number_ids, data.users)
                except ValueError as exc:
                    raise HTTPException(422,str(exc))
                details.update(country=data.number_country,number_ids=data.number_ids,seats=data.users)
            elif os.getenv('DIALNYTICS_REQUIRE_OWNED_NUMBERS') == '1':
                raise HTTPException(422,'Select one owned number for each user before checkout.')
        if data.kind=='demo':
            if data.preferred_date:
                try:
                    if date.fromisoformat(data.preferred_date)<now().date(): raise ValueError()
                except ValueError: raise HTTPException(422,'Choose a current or future preferred date.')
            details.update(duration_minutes=15,preferred_date=data.preferred_date,preferred_time=data.preferred_time,timezone=data.timezone,confirmation='pending')
        if data.kind=='quote': details.update(plan=data.plan or 'custom',users=data.users)
        plain=data.model_dump(mode='json');plain.pop('idempotency_key');plain.pop('website')
        # Password must never be stored in request JSON, audit logs, or payload hashes.
        supplied_password=plain.pop('dialer_password', '')
        digest=sha(json.dumps(plain,sort_keys=True)); key=str(data.idempotency_key)
        def receipt(row):
            text_lines=[f'Hello Dialnytics, my {row.kind} request reference is {row.reference}.',f'Name: {row.name}']
            if row.kind=='order':
                text_lines += [f'Plan: {row.details["plan_name"]}',f'Users: {row.details["users"]}',f'Monthly total: '+('$'+row.details['monthly_total']+' USD' if row.details.get('monthly_total') else 'Custom quote required'),f'Payment preference: {row.details["payment"]}']
                if row.details.get('countries'): text_lines.append('Destinations: '+', '.join(row.details['countries']))
                if row.details.get('addons'): text_lines.append('Add-ons: '+', '.join(a['name'] for a in row.details['addons']))
                if row.details.get('one_time_total') not in (None,'0.00'): text_lines.append('One-time SMS registration: $'+row.details['one_time_total']+' USD')
                if row.details.get('taxes_included'): text_lines.append('Prices include taxes.')
            if row.kind=='demo': text_lines.append('Please confirm the timing of my 15-minute demo.')
            text_lines.append('Please confirm the next steps.');msg='\n'.join(text_lines)
            # Manual payments have a server-authoritative 60-minute approval deadline.
            # This timestamp is informational; the approval endpoint enforces it.
            created=aware(row.created_at)
            deadline=(created+timedelta(minutes=60)).isoformat() if row.kind=='order' and row.details.get('payment') in ('bank','usdt') and row.status=='new' else None
            out={'payment_deadline':deadline,'saved':True,'reference':row.reference,'kind':row.kind,'quote':row.details if row.kind=='order' else None,
                 'whatsapp_url':'https://wa.me/'+BUSINESS['whatsapp']+'?'+urlencode({'text':msg}),'whatsapp_message':msg}
            if row.kind=='order' and row.details.get('payment')=='stripe' and settings.stripe_ready and row.details.get('monthly_total') and row.status=='new':
                try:
                    session=create_checkout(settings.stripe_secret_key,checkout_params(row.details,row.reference,row.email,settings.base_url,row.details['plan']),'dny-'+row.reference)
                    out['checkout_url']=session.get('url')
                except RuntimeError as exc: out['checkout_error']=str(exc)+' Continue on WhatsApp and we will send a card payment link.'
            return out
        with DB() as db:
            existing=db.scalar(select(Submission).where(Submission.idempotency_key==key))
            if existing:
                if existing.payload_hash!=digest: raise HTTPException(409,'This request key was already used. Reload before sending a different request.')
                return receipt(existing)
        rate_limit(request,'public',15,3600)
        row=Submission(id=str(uuid.uuid4()),reference='DNY-'+now().strftime('%y%m%d')+'-'+secrets.token_hex(6).upper(),
                       idempotency_key=key,payload_hash=digest,kind=data.kind,name=data.name,email=str(data.email).lower(),phone=data.phone,
                       company=data.company,subject=data.subject,message=data.message,details=details,status='new')
        try:
            with DB.begin() as db:
                db.add(row); db.flush()
                if data.kind=='order' and data.number_ids:
                    from .checkout_inventory import validate_inventory_ownership
                    from .number_reservations import reserve_numbers, InventoryConflict
                    try:
                        validate_inventory_ownership(db,data.number_country,data.number_ids)
                        reserve_numbers(db,row.reference,data.number_ids)
                    except (ValueError,InventoryConflict) as exc:
                        raise HTTPException(409,str(exc))
                if data.kind=='order' and supplied_password:
                    from .credential_vault import store_credentials
                    store_credentials(db,os.environ['DIALNYTICS_SIGNUP_FERNET_KEY'],row.reference,
                                      {'email':str(data.email).lower(),'password':supplied_password},ttl_minutes=120)
                db.add(MailJob(id=str(uuid.uuid4()),submission_id=row.id))
        except IntegrityError:
            with DB() as db:
                existing=db.scalar(select(Submission).where(Submission.idempotency_key==key))
                if existing and existing.payload_hash==digest: return receipt(existing)
            raise HTTPException(409,'A matching request may already exist. Please contact the team before retrying.')
        except SQLAlchemyError:
            log.exception('Marketing request could not be saved')
            raise HTTPException(503,'Your request was not saved. Please retry or contact us on WhatsApp directly.')
        return receipt(row)

    @app.get('/admin/login',response_class=HTMLResponse)
    def login_page(request:Request,error:str=''):
        if admin_session(request): return RedirectResponse('/admin',status_code=303)
        token=form_token(settings.secret,'login')
        res=render(request,'admin_login.html',{'login_csrf':token,'error':'Sign-in failed. Check your details and try again.' if error else '', 'page_title':'Marketing admin sign in'})
        res.set_cookie('mkt_login',token,max_age=7200,httponly=True,secure=settings.production,samesite='lax')
        return res
    @app.post('/admin/login')
    def login(request:Request,email:str=Form(...),password:str=Form(...),csrf:str=Form(...)):
        rate_limit(request,'login',8,900)
        if not hmac.compare_digest(csrf,request.cookies.get('mkt_login','')) or not valid_form_token(settings.secret,csrf,'login'):
            raise HTTPException(403,'Sign-in form expired. Reload the page.')
        password_ok=verify_password(password,settings.admin_password_hash)
        if not password_ok or email.strip().lower()!=settings.admin_email:
            return RedirectResponse('/admin/login?error=1',status_code=303)
        token=secrets.token_urlsafe(48)
        with DB.begin() as db:
            db.execute(delete(AdminSession).where(AdminSession.expires_at<now()))
            db.add(AdminSession(token_hash=sha(token),email=settings.admin_email,csrf=secrets.token_hex(32),credential_tag=sha(settings.admin_password_hash),expires_at=now()+timedelta(hours=8)))
            db.add(Audit(actor=settings.admin_email,action='login'))
        res=RedirectResponse('/admin',status_code=303)
        res.set_cookie('mkt_admin',token,max_age=28800,httponly=True,secure=settings.production,samesite='lax')
        res.delete_cookie('mkt_login')
        return res
    @app.post('/admin/logout')
    def logout(request:Request,csrf:str=Form(...)):
        sess=admin_required(request,csrf)
        with DB.begin() as db:
            audit(db,sess,'logout')
            db.execute(delete(AdminSession).where(AdminSession.token_hash==sess.token_hash))
        res=RedirectResponse('/admin/login',status_code=303);res.delete_cookie('mkt_admin');return res

    def query_requests(kind='',status='',q=''):
        qry=select(Submission)
        if kind in ADMIN_KINDS: qry=qry.where(Submission.kind==kind)
        if status in STATUSES: qry=qry.where(Submission.status==status)
        if q:
            term=q[:150]
            qry=qry.where(or_(Submission.name.icontains(term,autoescape=True),Submission.email.icontains(term,autoescape=True),Submission.reference.icontains(term,autoescape=True),Submission.company.icontains(term,autoescape=True),Submission.phone.icontains(term,autoescape=True)))
        return qry
    @app.get('/admin',response_class=HTMLResponse)
    @app.get('/admin/',response_class=HTMLResponse)
    def inbox(request:Request,kind:str='',status:str='',q:str='',page:int=1):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        page=max(1,min(page,100000))
        qry=query_requests(kind,status,q)
        with DB() as db:
            count=db.scalar(select(func.count()).select_from(qry.subquery()))
            rows=db.scalars(qry.order_by(Submission.created_at.desc()).offset((page-1)*25).limit(25)).all()
            stats=dict(db.execute(select(Submission.kind,func.count()).group_by(Submission.kind)).all())
            unread=db.scalar(select(func.count()).select_from(Submission).where(Submission.status=='new'))
            pending_mail=db.scalar(select(func.count()).select_from(MailJob).where(MailJob.status!='sent'))
        return render(request,'admin_inbox.html',{'page_title':'Marketing enquiries','admin':sess,'rows':rows,'stats':stats,'unread':unread,'count':count,'page':page,'pages':max(1,math.ceil(count/25)), 'kind':kind,'status':status,'q':q,'statuses':STATUSES,'kinds':ADMIN_KINDS,'mail_ready':settings.mail_ready,'pending_mail':pending_mail,'pager_query':urlencode({'kind':kind,'status':status,'q':q})})
    @app.get('/admin/renewals', response_class=HTMLResponse)
    def admin_renewals(request: Request):
        sess = admin_session(request)
        if not sess:
            return RedirectResponse('/admin/login', status_code=303)
        from .renewal_ledger import SubscriptionTerm, RenewalReceipt
        from .renewal_sync import RenewalSyncJob
        with DB() as db:
            jobs = db.scalars(select(RenewalSyncJob).order_by(RenewalSyncJob.next_attempt.desc()).limit(100)).all()
            terms = db.scalars(select(SubscriptionTerm).order_by(SubscriptionTerm.paid_through.desc()).limit(100)).all()
            receipts = db.scalars(select(RenewalReceipt).order_by(RenewalReceipt.confirmed_at.desc()).limit(100)).all()
            # Materialize rows while the session is open.
            jobs_data = [{'account_id': j.account_id, 'status': j.status,
                          'target': j.target_paid_through, 'attempts': j.attempts,
                          'error': j.last_error} for j in jobs]
            terms_data = [{'account_id': t.account_id, 'paid_through': t.paid_through,
                           'renewals': t.renewal_count} for t in terms]
            receipts_data = [{'payment_id': r.payment_id, 'account_id': r.account_id,
                              'confirmed_at': r.confirmed_at} for r in receipts]
        return render(request, 'admin_renewals.html', {'page_title': 'Subscription renewals',
                      'admin': sess, 'jobs': jobs_data, 'terms': terms_data,
                      'receipts': receipts_data})

    @app.post('/admin/renewals/manual-approve')
    def admin_approve_manual_renewal(request: Request,
                                     order_reference: str = Form(...),
                                     payment_reference: str = Form(...),
                                     payment_method: str = Form(...),
                                     verified: str = Form(''),
                                     csrf: str = Form(...)):
        # This is an admin assertion of external payment verification, NOT
        # proof of payment from a customer. Never expose as a public route.
        sess = admin_required(request, csrf)
        from .manual_renewal import approve_manual_renewal, ManualRenewalError
        try:
            if verified != 'yes':
                raise ManualRenewalError('Confirm independent payment verification first')
            with DB.begin() as db:
                paid_through, created = approve_manual_renewal(
                    db, order_reference=order_reference.strip(),
                    payment_reference=payment_reference.strip(),
                    payment_method=payment_method, actor=sess.email,
                    verified=True, confirmed_at=now())
                audit(db, sess, 'manual renewal '+('approved' if created else 'duplicate'),
                      order_reference.strip())
        except (ManualRenewalError, ValueError) as exc:
            return RedirectResponse('/admin/renewals?'+urlencode({'error':str(exc)}), status_code=303)
        return RedirectResponse('/admin/renewals?'+urlencode({'saved':'1' if created else 'duplicate'}), status_code=303)

    @app.get('/admin/manual-payments', response_class=HTMLResponse)
    def admin_manual_payments(request: Request):
        sess = admin_session(request)
        if not sess: return RedirectResponse('/admin/login', status_code=303)
        with DB() as db:
            orders = db.scalars(select(Submission).where(Submission.kind == 'order',
                Submission.status.in_(['new','expired','paid']))
                .order_by(Submission.created_at.desc()).limit(300)).all()
            data = [{'reference': o.reference, 'name': o.name, 'email': o.email,
                     'status': o.status, 'created_at': o.created_at,
                     'payment': (o.details or {}).get('payment'),
                     'total': (o.details or {}).get('monthly_total'),
                     'users': (o.details or {}).get('users')}
                    for o in orders if (o.details or {}).get('payment') in ('bank','usdt')]
        return render(request, 'admin_manual_payments.html', {'page_title':'Manual payments',
            'admin':sess, 'orders':data, 'error':request.query_params.get('error',''),
            'saved':request.query_params.get('saved','')})

    @app.post('/admin/manual-payments/approve')
    def admin_approve_manual_payment(request: Request, reference: str = Form(...), csrf: str = Form(...)):
        sess = admin_required(request, csrf)
        from .manual_payment_approval import approve_manual_order, ApprovalError
        try:
            with DB.begin() as db:
                outcome = approve_manual_order(db, reference, actor=sess.email)
                audit(db, sess, 'manual payment '+outcome, reference)
        except ApprovalError as exc:
            return RedirectResponse('/admin/manual-payments?'+urlencode({'error':str(exc)}), status_code=303)
        return RedirectResponse('/admin/manual-payments?saved=1', status_code=303)

    @app.get('/admin/provisioning',response_class=HTMLResponse)
    def admin_provisioning(request:Request, status:str='', page:int=1):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        from .database import ProvisioningJob
        allowed={'pending','processing','retry','completed'}
        if status and status not in allowed: raise HTTPException(422,'Invalid job status')
        page=max(1,min(page,10000))
        with DB() as db:
            query=select(ProvisioningJob)
            if status: query=query.where(ProvisioningJob.status==status)
            jobs=db.scalars(query.order_by(ProvisioningJob.next_attempt.desc()).offset((page-1)*50).limit(50)).all()
            counts=dict(db.execute(select(ProvisioningJob.status,func.count()).group_by(ProvisioningJob.status)).all())
        return render(request,'admin_provisioning.html',{'page_title':'Account provisioning',
                      'admin':sess,'jobs':jobs,'counts':counts,'selected_status':status,'page':page})

    @app.get('/admin/requests/{record_id}',response_class=HTMLResponse)
    def detail(request:Request,record_id:str):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        with DB() as db:
            row=db.get(Submission,record_id)
            if not row: raise HTTPException(404,'Request not found.')
            notes=db.scalars(select(Note).where(Note.submission_id==record_id).order_by(Note.created_at.desc())).all()
            job=db.scalar(select(MailJob).where(MailJob.submission_id==record_id))
        return render(request,'admin_detail.html',{'page_title':row.reference,'admin':sess,'row':row,'notes':notes,'job':job,'statuses':STATUSES,'mail_ready':settings.mail_ready})
    @app.post('/admin/requests/{record_id}')
    def update_request(request:Request,record_id:str,csrf:str=Form(...),status:str=Form(...),note:str=Form('')):
        sess=admin_required(request,csrf)
        if status not in STATUSES or len(note)>5000: raise HTTPException(422,'Invalid status or note length.')
        with DB.begin() as db:
            row=db.get(Submission,record_id)
            if not row: raise HTTPException(404,'Request not found.')
            if row.status!=status:
                audit(db,sess,'status: '+row.status+' -> '+status,row.reference)
                row.status=status
            row.updated_at=now()
            if note.strip():
                db.add(Note(submission_id=record_id,body=note.strip(),author=sess.email));audit(db,sess,'note added',row.reference)
        return RedirectResponse('/admin/requests/'+record_id+'?saved=1',status_code=303)
    @app.post('/admin/requests/{record_id}/email')
    def retry_mail(request:Request,record_id:str,csrf:str=Form(...)):
        sess=admin_required(request,csrf)
        with DB.begin() as db:
            job=db.scalar(select(MailJob).where(MailJob.submission_id==record_id))
            if not job: raise HTTPException(404,'Email job not found.')
            if job.status=='sending' and job.lease_until and aware(job.lease_until)>now(): raise HTTPException(409,'Email is currently being sent.')
            job.status='pending';job.attempts=0;job.next_attempt=now();job.last_error=''
            audit(db,sess,'email retry requested',db.get(Submission,record_id).reference)
        return RedirectResponse('/admin/requests/'+record_id,status_code=303)
    @app.post('/admin/requests/{record_id}/delete')
    def erase(request:Request,record_id:str,csrf:str=Form(...),confirm:str=Form(...)):
        sess=admin_required(request,csrf)
        with DB.begin() as db:
            row=db.get(Submission,record_id)
            if not row: raise HTTPException(404,'Request not found.')
            if confirm!=row.reference: raise HTTPException(422,'Type the exact request reference to confirm deletion.')
            audit(db,sess,'request erased',row.reference);db.delete(row)
        return RedirectResponse('/admin?deleted=1',status_code=303)
    @app.get('/admin/export.csv')
    def export(request:Request,kind:str='',status:str='',q:str=''):
        sess=admin_required(request)
        with DB.begin() as db:
            rows=db.scalars(query_requests(kind,status,q).order_by(Submission.created_at.desc()).limit(10000)).all()
            audit(db,sess,'export '+str(len(rows))+' requests')
        out=io.StringIO();writer=csv.writer(out)
        writer.writerow(['Reference','Type','Status','Name','Email','Phone','Company','Created UTC','Plan','Users','Monthly USD','Payment preference','Subject','Message'])
        for r in rows:
            writer.writerow([csv_safe(v) for v in [r.reference,r.kind,r.status,r.name,r.email,r.phone,r.company,aware(r.created_at).isoformat(),r.details.get('plan_name',''),r.details.get('users',''),r.details.get('monthly_total',''),r.details.get('payment',''),r.subject,r.message]])
        return Response('\ufeff'+out.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':'attachment; filename="dialnytics-enquiries.csv"'})
    @app.get('/api/checkout/inventory-mode')
    def checkout_inventory_mode():
        return {'required':os.getenv('DIALNYTICS_REQUIRE_OWNED_NUMBERS')=='1'}

    @app.get('/api/numbers/available')
    def available_owned_numbers(country: str = 'US', number_type: str = 'local'):
        if country not in ('US','CA','GB') or number_type not in ('local','toll_free'):
            raise HTTPException(422,'Unsupported number filter')
        with DB() as db:
            rows=db.scalars(select(PhoneInventory).where(PhoneInventory.country==country,
                PhoneInventory.number_type==number_type,PhoneInventory.status=='available')
                .order_by(PhoneInventory.e164).limit(200)).all()
            return {'numbers':[{'id':r.id,'number':r.e164,'country':r.country,'type':r.number_type} for r in rows]}

    @app.get('/admin/numbers',response_class=HTMLResponse)
    def admin_numbers(request:Request):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        with DB() as db: rows=db.scalars(select(PhoneInventory).order_by(PhoneInventory.country,PhoneInventory.e164)).all()
        return render(request,'admin_numbers.html',{'page_title':'Owned number inventory','admin':sess,'rows':rows})

    @app.post('/admin/numbers')
    def admin_number_add(request:Request,csrf:str=Form(...),number:str=Form(...),country:str=Form(...),
                         provider:str=Form(...),number_type:str=Form('local')):
        import re
        sess=admin_session(request)
        if not sess: raise HTTPException(403,'Admin required')
        if not hmac.compare_digest(csrf,sess.csrf): raise HTTPException(403,'Invalid admin CSRF')
        if not re.fullmatch(r'\+[1-9][0-9]{7,14}',number): raise HTTPException(422,'Use E.164 number')
        if country not in ('US','CA','GB') or provider not in ('telnyx','twilio') or number_type not in ('local','toll_free'):
            raise HTTPException(422,'Invalid number configuration')
        if (country=='GB') != (provider=='twilio'):
            raise HTTPException(422,'UK must use Twilio; US/CA must use Telnyx')
        with DB.begin() as db:
            if db.scalar(select(PhoneInventory.id).where(PhoneInventory.e164==number)):
                raise HTTPException(409,'Number already exists')
            db.add(PhoneInventory(id=str(uuid.uuid4()),e164=number,country=country,provider=provider,number_type=number_type))
            audit(db,sess,'number added',number)
        return RedirectResponse('/admin/numbers',status_code=303)

    @app.get('/admin/activity',response_class=HTMLResponse)
    def activity(request:Request):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        with DB() as db: rows=db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200)).all()
        return render(request,'admin_activity.html',{'page_title':'Admin activity','admin':sess,'rows':rows,'mail_ready':settings.mail_ready})

    @app.post('/webhooks/stripe')
    async def stripe_webhook(request:Request):
        if not settings.stripe_ready: raise HTTPException(404,'Not found.')
        body=await request.body()
        try: event=verify_webhook(body,request.headers.get('stripe-signature',''),settings.stripe_webhook_secret)
        except (ValueError,json.JSONDecodeError): raise HTTPException(400,'Invalid signature.')
        obj=(event.get('data') or {}).get('object') or {}
        kind=event.get('type','')
        ref=obj.get('client_reference_id') or (obj.get('metadata') or {}).get('reference') or ''
        if kind == 'invoice.paid':
            from .stripe_renewals import process_paid_invoice
            with DB.begin() as db:
                outcome, order_ref = process_paid_invoice(db, obj)
            # Pending renewals are durably stored and replayed by the worker.
            log.info('Stripe recurring invoice outcome=%s order=%s', outcome, order_ref)
            return {'received': True}
        if kind in ('customer.subscription.deleted', 'invoice.payment_failed'):
            from .subscription_events import apply_subscription_event
            with DB.begin() as db:
                outcome = apply_subscription_event(db, kind, obj, timestamp=now())
            log.info('Stripe subscription lifecycle outcome=%s', outcome)
            return {'received': True}
        if not ref: return {'received':True}
        with DB.begin() as db:
            row=db.scalar(select(Submission).where(Submission.reference==ref,Submission.kind=='order'))
            if not row: return {'received':True}
            details=dict(row.details or {}); card=dict(details.get('card_payment') or {})
            if kind in ('checkout.session.completed', 'checkout.session.async_payment_succeeded'):
                # Checkout can complete before an asynchronous payment settles.
                # Never grant paid status unless Stripe explicitly confirms payment.
                if obj.get('payment_status') != 'paid':
                    return {'received':True}
                session_id=obj.get('id')
                if card.get('status')=='active' and card.get('session')==session_id:
                    return {'received':True}  # webhook retries must not duplicate paid notes
                card.update(session=session_id,subscription=obj.get('subscription'),
                            customer=obj.get('customer'),amount_total=obj.get('amount_total'),
                            paid_at=now().isoformat(),status='active')
                row.status='paid'
                from .provisioning_queue import enqueue_paid_order
                db.flush()
                enqueue_paid_order(db, row.reference)
                db.add(Note(submission_id=row.id,
                    body='Stripe payment verified. Account provisioning still requires a separate secure workflow.',
                    author='Stripe'))
            elif kind=='checkout.session.async_payment_failed':
                if row.status=='paid': return {'received':True}
                card.update(status='payment_failed',failed_at=now().isoformat())
            elif kind=='customer.subscription.deleted':
                card.update(status='cancelled',cancelled_at=now().isoformat())
                db.add(Note(submission_id=row.id,body='Stripe subscription cancelled.',author='Stripe'))
            elif kind=='invoice.payment_failed':
                card.update(status='payment_failed',failed_at=now().isoformat())
                db.add(Note(submission_id=row.id,body='Stripe renewal payment failed.',author='Stripe'))
            else: return {'received':True}
            details['card_payment']=card; row.details=details; row.updated_at=now()
        return {'received':True}

    @app.get('/order/thanks/',response_class=HTMLResponse)
    def order_thanks(request:Request,ref:str=''):
        row=None
        if ref and len(ref)<=32:
            with DB() as db: row=db.scalar(select(Submission).where(Submission.reference==ref,Submission.kind=='order'))
        return render(request,'thanks.html',{'page_title':'Thank you for your order','row':row})

    @app.post('/api/newsletter')
    def newsletter(request:Request,data:NewsletterData):
        require_public_csrf(request)
        if data.website: raise HTTPException(400,'Unable to subscribe.')
        if not data.consent: raise HTTPException(422,'Please agree to receive occasional emails.')
        email=str(data.email).lower(); key=str(data.idempotency_key)
        with DB() as db:
            if db.scalar(select(Submission).where(Submission.kind=='newsletter',Submission.email==email)): return {'subscribed':True}
        rate_limit(request,'newsletter',5,3600)
        row=Submission(id=str(uuid.uuid4()),reference='DNL-'+now().strftime('%y%m%d')+'-'+secrets.token_hex(6).upper(),
                       idempotency_key=key,payload_hash=sha(email),kind='newsletter',name='Newsletter subscriber',email=email,
                       details={'source':'website footer'},status='new')
        try:
            with DB.begin() as db: db.add(row)
        except IntegrityError: return {'subscribed':True}
        except SQLAlchemyError:
            log.exception('Newsletter signup could not be saved')
            raise HTTPException(503,'Could not subscribe right now. Please try again later.')
        return {'subscribed':True}

    def pricing_groups(values):
        groups=[]
        for key,label,group,default,lo,hi in PRICE_FIELDS:
            if not groups or groups[-1][0]!=group: groups.append((group,[]))
            groups[-1][1].append({'key':key,'label':label,'value':values.get(key,usd(DEFAULT_PRICES[key])),'default':usd(DEFAULT_PRICES[key]),'min':lo,'max':hi})
        return groups
    @app.get('/admin/pricing',response_class=HTMLResponse)
    def admin_pricing(request:Request):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        load_prices(force=True)
        with DB() as db: row=db.get(Setting,'prices')
        return render(request,'admin_pricing.html',{'page_title':'Pricing','admin':sess,'groups':pricing_groups({k:usd(v) for k,v in PRICES.items()}),
            'row':row,'saved':request.query_params.get('saved'),'reset':request.query_params.get('reset'),'error':None,'preview':price_view()})
    @app.post('/admin/pricing',response_class=HTMLResponse)
    async def admin_pricing_save(request:Request):
        form=await request.form()
        sess=admin_required(request,str(form.get('csrf','')))
        action=str(form.get('action','save'))
        if action=='reset': values={k:v for k,v in DEFAULT_PRICES.items()}
        else:
            raw={k:str(form.get(k,'')) for k,*_ in PRICE_FIELDS}
            try: values=clean_prices(raw)
            except ValueError as exc:
                with DB() as db: row=db.get(Setting,'prices')
                return render(request,'admin_pricing.html',{'page_title':'Pricing','admin':sess,'groups':pricing_groups(raw),'row':row,'saved':None,'reset':None,'error':str(exc),'preview':price_view()},status=422)
        before={k:usd(v) for k,v in PRICES.items()}
        version=now().strftime('%Y-%m-%d')+'.admin-'+secrets.token_hex(3)
        with DB.begin() as db:
            row=db.get(Setting,'prices')
            payload={'values':{k:str(v) for k,v in values.items()},'version':version}
            if row: row.value=payload; row.updated_by=sess.email; row.updated_at=now()
            else: db.add(Setting(key='prices',value=payload,updated_by=sess.email,updated_at=now()))
            changed=[k for k,v in values.items() if usd(v)!=before.get(k)]
            audit(db,sess,('prices reset to defaults' if action=='reset' else 'prices updated: '+(', '.join(changed) or 'no change'))[:100],version[:32])
        load_prices(force=True)
        return RedirectResponse('/admin/pricing?'+('reset=1' if action=='reset' else 'saved=1'),status_code=303)

    register_chat(app,settings,DB,render,require_public_csrf,rate_limit,admin_session,admin_required,audit)

    special=['/','/pricing/','/numbers/','/get-started/','/book-demo/','/contact/','/support/','/custom-quote/','/faq/','/product/tour/','/tools/']+['/tools/'+t[0]+'/' for t in TOOLS]
    all_paths=sorted(set(special+list(PAGES)+list(COLLECTIONS)+['/numbers/'+s+'/' for s in list(PLANS)+['usa','canada']]+['/get-started/'+s+'/' for s in PLANS]))
    app.state.public_paths=all_paths
    @app.get('/sitemap.xml')
    def sitemap():
        from xml.sax.saxutils import escape
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(settings.base_url+p)+'</loc></url>' for p in all_paths)+'</urlset>',media_type='application/xml')
    @app.get('/robots.txt')
    def robots(): return Response('User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nDisallow: /webhooks/\nSitemap: '+settings.base_url+'/sitemap.xml\n',media_type='text/plain')
    @app.get('/{path:path}',response_class=HTMLResponse)
    def page(request:Request,path:str):
        route='/'+path.strip('/')+'/'
        if route in COLLECTIONS:
            title,eyebrow,desc,group=COLLECTIONS[route]
            return render(request,'collection.html',{'page_title':title,'eyebrow':eyebrow,'description':desc,'items':[v for v in PAGES.values() if v.get('group')==group]})
        if route in PAGES:
            p=PAGES[route]
            return render(request,'content.html',{'page_title':p['title'],'description':p['description'],'page':p})
        return render(request,'404.html',{'page_title':'Page not found'},status=404)
    return app

app=create_app()
