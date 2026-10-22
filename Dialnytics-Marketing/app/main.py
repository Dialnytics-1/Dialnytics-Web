"""Independent Dialnytics marketing app. Contains no telephony credentials or dialer writes."""
import asyncio, contextlib, csv, io, json, logging, secrets, uuid, math, time, hmac
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
from .database import make_database, init_database, Submission, AdminSession, Note, MailJob, Audit, RateBucket
from .security import now, sha, verify_password, form_token, valid_form_token, csv_safe
from .catalog import BUSINESS, PLANS, FEATURES, EUROPE_COUNTRIES, price_quote, client_catalog
from .content import PAGES, COLLECTIONS, PRODUCT_LINKS, SOLUTION_LINKS, FAQ
from .mail import deliver_one

log=logging.getLogger('dialnytics.marketing')
STATUSES=['new','contacted','awaiting_payment','paid','demo_confirmed','closed','spam']
KINDS=['order','contact','demo','quote','support']

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
    payment: str=Field(default='',max_length=30)
    number_preference: str=Field(default='',max_length=200)
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

    @asynccontextmanager
    async def lifespan(app):
        settings.validate()
        init_database(engine)
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

        response = await call_next(request)

        response.headers['X-Content-Type-Options'] = 'nosniff'
        response.headers['X-Frame-Options'] = 'DENY'
        response.headers['Referrer-Policy'] = 'strict-origin-when-cross-origin'
        response.headers['Permissions-Policy'] = (
            'camera=(), microphone=(), geolocation=()'
        )
        response.headers['Content-Security-Policy'] = (
    "default-src 'self'; "
    "script-src 'self' 'sha256-REPLACE_WITH_PIXEL_SCRIPT_HASH' https://connect.facebook.net; "
    "style-src 'self' 'unsafe-inline'; "
    "img-src 'self' data: https://www.facebook.com; "
    "font-src 'self'; "
    "connect-src 'self' https://www.facebook.com https://connect.facebook.net; "
    "form-action 'self'; "
    "frame-ancestors 'none'; "
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
             'catalog':client_catalog(),'csrf':csrf,'year':now().year,
             'base_url':settings.base_url,'canonical':settings.base_url+request.url.path,
             'current_path':request.url.path,'page_title':'Business calling, without the extra layers.',
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
    def home(request:Request): return render(request,'home.html')
    @app.get('/pricing/',response_class=HTMLResponse)
    def pricing(request:Request): return render(request,'pricing.html',{'page_title':'One plan price. Everything included.'})
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
    @app.get('/product/tour/',response_class=HTMLResponse)
    def tour(request:Request): return render(request,'tour.html',{'page_title':'A closer look at your calling workflow.'})
    @app.get('/faq/',response_class=HTMLResponse)
    def faq_page(request:Request): return render(request,'faq.html',{'page_title':'A few answers before your next call.'})
    @app.get('/book-demo/',response_class=HTMLResponse)
    def demo(request:Request): return render(request,'form.html',{'kind':'demo','page_title':'See Dialnytics in 15 minutes.','form_title':'Request your guided demo','description':'Tell us what your team needs. We will send you a WhatsApp message to confirm the date and time of your 15-minute demo.'})
    @app.get('/contact/',response_class=HTMLResponse)
    def contact(request:Request): return render(request,'form.html',{'kind':'contact','page_title':"Let's talk about your next step.",'form_title':'Send us a message'})
    @app.get('/support/',response_class=HTMLResponse)
    def support(request:Request): return render(request,'form.html',{'kind':'support','page_title':'A human team, when you need help.','form_title':'Contact support','description':BUSINESS['support_hours']+'. Activation is available 24/7, separately from support hours.'})
    @app.get('/custom-quote/',response_class=HTMLResponse)
    def quote_page(request:Request): return render(request,'form.html',{'kind':'quote','page_title':'A plan built around your destinations.','form_title':'Request a custom quote'})
    @app.get('/trial-and-demo/')
    def old_demo(): return RedirectResponse('/book-demo/',status_code=301)
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
        try: return price_quote(data.get('plan'),data.get('users'),data.get('countries',[]))
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
            try: details=price_quote(data.plan,data.users,data.countries)
            except ValueError as exc: raise HTTPException(422,str(exc))
            if data.payment not in ('bank','usdt','stripe'): raise HTTPException(422,'Choose a payment preference.')
            details.update(payment=data.payment,number_preference=data.number_preference)
        if data.kind=='demo':
            if data.preferred_date:
                try:
                    if date.fromisoformat(data.preferred_date)<now().date(): raise ValueError()
                except ValueError: raise HTTPException(422,'Choose a current or future preferred date.')
            details.update(duration_minutes=15,preferred_date=data.preferred_date,preferred_time=data.preferred_time,timezone=data.timezone,confirmation='pending')
        if data.kind=='quote': details.update(plan=data.plan or 'custom',users=data.users)
        plain=data.model_dump(mode='json');plain.pop('idempotency_key');plain.pop('website')
        digest=sha(json.dumps(plain,sort_keys=True)); key=str(data.idempotency_key)
        def receipt(row):
            text_lines=[f'Hello Dialnytics, my {row.kind} request reference is {row.reference}.',f'Name: {row.name}']
            if row.kind=='order':
                text_lines += [f'Plan: {row.details["plan_name"]}',f'Users: {row.details["users"]}',f'Monthly total: '+('$'+row.details['monthly_total']+' USD' if row.details.get('monthly_total') else 'Custom quote required'),f'Payment preference: {row.details["payment"]}']
                if row.details.get('countries'): text_lines.append('Destinations: '+', '.join(row.details['countries']))
            if row.kind=='demo': text_lines.append('Please confirm the timing of my 15-minute demo.')
            text_lines.append('Please confirm the next steps.');msg='\n'.join(text_lines)
            return {'saved':True,'reference':row.reference,'kind':row.kind,'quote':row.details if row.kind=='order' else None,
                    'whatsapp_url':'https://wa.me/'+BUSINESS['whatsapp']+'?'+urlencode({'text':msg}),'whatsapp_message':msg}
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
        if kind in KINDS: qry=qry.where(Submission.kind==kind)
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
        return render(request,'admin_inbox.html',{'page_title':'Marketing enquiries','admin':sess,'rows':rows,'stats':stats,'unread':unread,'count':count,'page':page,'pages':max(1,math.ceil(count/25)), 'kind':kind,'status':status,'q':q,'statuses':STATUSES,'kinds':KINDS,'mail_ready':settings.mail_ready,'pending_mail':pending_mail,'pager_query':urlencode({'kind':kind,'status':status,'q':q})})
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
    @app.get('/admin/activity',response_class=HTMLResponse)
    def activity(request:Request):
        sess=admin_session(request)
        if not sess: return RedirectResponse('/admin/login',status_code=303)
        with DB() as db: rows=db.scalars(select(Audit).order_by(Audit.created_at.desc()).limit(200)).all()
        return render(request,'admin_activity.html',{'page_title':'Admin activity','admin':sess,'rows':rows,'mail_ready':settings.mail_ready})

    special=['/','/pricing/','/numbers/','/get-started/','/book-demo/','/contact/','/support/','/custom-quote/','/faq/','/product/tour/']
    all_paths=sorted(set(special+list(PAGES)+list(COLLECTIONS)+['/numbers/'+s+'/' for s in list(PLANS)+['usa','canada']]+['/get-started/'+s+'/' for s in PLANS]))
    app.state.public_paths=all_paths
    @app.get('/sitemap.xml')
    def sitemap():
        from xml.sax.saxutils import escape
        return Response('<?xml version="1.0" encoding="UTF-8"?><urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'+''.join('<url><loc>'+escape(settings.base_url+p)+'</loc></url>' for p in all_paths)+'</urlset>',media_type='application/xml')
    @app.get('/robots.txt')
    def robots(): return Response('User-agent: *\nAllow: /\nDisallow: /admin\nDisallow: /api/\nSitemap: '+settings.base_url+'/sitemap.xml\n',media_type='text/plain')
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
