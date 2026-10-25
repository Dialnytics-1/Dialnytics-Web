import uuid, re, io, csv
from urllib.parse import urlsplit
from pathlib import Path
from datetime import timedelta
import pytest
from bs4 import BeautifulSoup
from fastapi.testclient import TestClient
from sqlalchemy import select, text
from app.main import create_app
from app.settings import Settings
from app.security import hash_password, verify_password, now, csv_safe
from app.database import Submission, Note, MailJob, Audit, Base, init_database
from app.catalog import price_quote, PLANS, EUROPE_COUNTRIES

@pytest.fixture
def app(tmp_path):
    settings=Settings(secret='test-only-secret-'+'x'*40,admin_password_hash=hash_password('OnlyForTests-Password123'),database_url='sqlite:///'+str(tmp_path/'test.sqlite3'),base_url='http://testserver',worker=False)
    return create_app(settings)
@pytest.fixture
def client(app):
    with TestClient(app) as client: yield client

def public_token(client,path='/contact/'):
    page=client.get(path)
    assert page.status_code==200
    return BeautifulSoup(page.text,'html.parser').find('meta',attrs={'name':'csrf-token'})['content']
def request_payload(**changes):
    return dict(kind='contact',name='Example Person',email='person@example.org',message='Please explain the available plans.',consent=True,idempotency_key=str(uuid.uuid4()),**changes)
def submit(client,payload):
    return client.post('/api/requests',json=payload,headers={'X-CSRF-Token':public_token(client)})
def login(client):
    r=client.get('/admin/login');s=BeautifulSoup(r.text,'html.parser')
    r=client.post('/admin/login',data={'email':'admin@dialnytics.co.uk','password':'OnlyForTests-Password123','csrf':s.find('input',attrs={'name':'csrf'})['value']},follow_redirects=False)
    assert r.status_code==303
    assert 'httponly' in r.headers['set-cookie'].lower()
    return client.cookies.get('mkt_admin')
def admin_csrf(client,record_id):
    r=client.get('/admin/requests/'+record_id)
    return BeautifulSoup(r.text,'html.parser').find('input',attrs={'name':'csrf'})['value']

@pytest.mark.parametrize('plan,users,expected',[('usa-canada',1,'22.00'),('usa-canada',2,'40.00'),('usa-canada',3,'54.00'),('usa-canada',5,'90.00'),('uk',1,'29.00'),('uk',2,'58.00'),('australia',3,'132.00'),('japan',2,'128.00'),('global',1,'179.00'),('custom',3,None),('europe',1,None)])
def test_price(plan,users,expected):
    q=price_quote(plan,users);assert q['monthly_total']==expected;assert q['extra_charges']=='0.00';assert q['setup_fee']=='0.00'
@pytest.mark.parametrize('count,expected',[(1,'44.00'),(2,'79.00'),(3,'110.60'),(4,'137.40'),(5,'159.85'),(6,'178.52')])
def test_europe_pricing(count,expected): assert price_quote('uk-to-europe',1,EUROPE_COUNTRIES[:count])['monthly_total']==expected
@pytest.mark.parametrize('users',[0,-1,101,True,1.5,'3'])
def test_bad_quantity(users):
    with pytest.raises(ValueError): price_quote('uk',users)
def test_duplicate_europe_destinations():
    with pytest.raises(ValueError): price_quote('uk-to-europe',1,['France','France'])
def test_real_html_routes(client,app):
    for path in app.state.public_paths:
        r=client.get(path)
        assert r.status_code==200,(path,r.text[:200])
        assert '<title>' in r.text,path
        assert 'Internal Server Error' not in r.text,path
        assert 'name="csrf-token"' in r.text,path
    assert len(app.state.public_paths)>100

def test_internal_links(client,app):
    paths=set()
    for path in ['/','/pricing/','/numbers/','/solutions/','/product/','/docs/','/blog/','/legal/','/compare/']:
        s=BeautifulSoup(client.get(path).text,'html.parser')
        for a in s.select('a[href]'):
            href=a['href']
            if href.startswith('/') and not href.startswith('//'): paths.add(urlsplit(href).path)
    for path in paths: assert client.get(path).status_code==200,path

def test_not_offered_routes(client):
    assert client.get('/refer-and-earn/').status_code==404
    assert 'not currently' in client.get('/product/sms/').text.lower()
    for path in ['/product/ai-insights/','/product/live-captions/','/product/floating-phone/']:
        assert 'Not currently available' in client.get(path).text

def test_save_and_idempotency(client,app):
    p=request_payload()
    r=submit(client,p);assert r.status_code==200,r.text
    assert r.json()['saved']
    again=submit(client,p);assert again.json()['reference']==r.json()['reference']
    with app.state.DB() as db:
        rows=db.scalars(select(Submission)).all();assert len(rows)==1
        assert rows[0].email=='person@example.org'
        assert len(db.scalars(select(MailJob)).all())==1
        assert db.scalar(select(MailJob)).status=='pending'
    p['message']='A different message for same key.'
    assert submit(client,p).status_code==409

def test_requires_csrf(client): assert client.post('/api/requests',json=request_payload()).status_code==403

def test_rejects_cross_origin(client):
    token=public_token(client)
    assert client.post('/api/requests',json=request_payload(),headers={'X-CSRF-Token':token,'Origin':'https://untrusted.example'}).status_code==403

def test_honeypot(client):
    p=request_payload(website='spam.example');assert submit(client,p).status_code==400

def test_consent_required(client):
    p=request_payload();p['consent']=False
    assert submit(client,p).status_code==422

def test_server_pricing_and_no_payment_claim(client,app):
    p=request_payload();p.update(kind='order',phone='+447700900123',plan='usa-canada',users=2,payment='stripe')
    r=submit(client,p);assert r.status_code==200,r.text
    assert r.json()['quote']['monthly_total']=='40.00'
    assert 'paid' not in r.json()
    with app.state.DB() as db: assert db.scalar(select(Submission)).status=='new'
    p['idempotency_key']=str(uuid.uuid4());p['monthly_total']='0.01'
    assert submit(client,p).status_code==422

def test_demo(client,app):
    p=request_payload();p.update(kind='demo',phone='+447700900123',preferred_date=(now()+timedelta(days=2)).date().isoformat(),preferred_time='15:00')
    r=submit(client,p);assert r.status_code==200,r.text
    with app.state.DB() as db:
        row=db.scalar(select(Submission));assert row.details['duration_minutes']==15;assert row.details['confirmation']=='pending'
    assert 'confirm' in r.json()['whatsapp_message'].lower()

def test_invalid_phone_and_date(client):
    p=request_payload();p.update(kind='demo',phone='localnumber');assert submit(client,p).status_code==422
    p['phone']='+447700900123';p['preferred_date']='2020-01-01';assert submit(client,p).status_code==422

def test_body_limit(client):
    token=public_token(client)
    assert client.post('/api/requests',content=b'x'*70000,headers={'Content-Type':'application/json','X-CSRF-Token':token}).status_code==413

def test_admin_flow(client,app):
    assert client.get('/admin',follow_redirects=False).status_code==303
    assert client.get('/admin/export.csv').status_code==401
    p=request_payload();submit(client,p)
    with app.state.DB() as db: row=db.scalar(select(Submission));rid,ref=row.id,row.reference
    login(client)
    assert ref in client.get('/admin').text
    token=admin_csrf(client,rid)
    assert client.post('/admin/requests/'+rid,data={'status':'contacted','note':'Called the prospect.','csrf':'wrong'}).status_code==403
    r=client.post('/admin/requests/'+rid,data={'status':'contacted','note':'Called the prospect.','csrf':token});assert r.status_code==200
    assert 'Called the prospect.' in r.text
    assert ref not in client.get('/admin?status=closed').text
    assert ref in client.get('/admin?q=Example').text
    export=client.get('/admin/export.csv');assert export.status_code==200 and ref in export.text
    assert client.post('/admin/requests/'+rid+'/delete',data={'csrf':token,'confirm':'wrong'}).status_code==422
    assert client.post('/admin/requests/'+rid+'/delete',data={'csrf':token,'confirm':ref}).status_code==200
    with app.state.DB() as db:
        assert db.get(Submission,rid) is None
        assert not db.scalars(select(Note)).all()
        assert not db.scalars(select(MailJob)).all()
        assert db.scalars(select(Audit)).all()
    client.post('/admin/logout',data={'csrf':token})
    assert client.get('/admin',follow_redirects=False).status_code==303

def test_admin_escaping(client,app):
    p=request_payload();p['message']='<img src=x onerror=alert(1)> This is a message.'
    submit(client,p);login(client)
    with app.state.DB() as db: rid=db.scalar(select(Submission)).id
    r=client.get('/admin/requests/'+rid)
    assert '&lt;img src=x onerror=alert(1)&gt;' in r.text
    assert '<img src=x' not in r.text

def test_csv_injection_guard():
    for v in ['=SUM(A1)','+447700900123','-5','@formula',' \t=evil']:
        assert csv_safe(v).startswith("'")
    assert csv_safe('Normal')=='Normal'

def test_security_headers(client):
    r=client.get('/')
    assert r.headers['x-frame-options']=='DENY'
    assert "script-src 'self'" in r.headers['content-security-policy']
    assert client.get('/admin/login').headers['cache-control']=='no-store'

def test_tour_is_frameable_only_on_same_origin(client):
    r=client.get('/static/product-tour/index.html')
    assert r.headers['x-frame-options']=='SAMEORIGIN'
    assert "frame-ancestors 'self'" in r.headers['content-security-policy']
    assert client.get('/').headers['x-frame-options']=='DENY'
    page=client.get('/product/tour/').text
    assert '/static/product-tour/dialnytics-product-tour.mp4' in page and '/static/js/tour-video.js' in page

def test_separate_database_guard(tmp_path):
    from app.database import make_database
    e,_=make_database('sqlite:///'+str(tmp_path/'wrong.sqlite'))
    with e.begin() as c:c.execute(text('CREATE TABLE dialnytics_users (id INTEGER PRIMARY KEY)'))
    with pytest.raises(RuntimeError,match='NEW separate'):init_database(e)

def test_postgres_schema_compiles():
    from sqlalchemy.schema import CreateTable
    from sqlalchemy.dialects import postgresql
    for table in Base.metadata.sorted_tables:
        sql=str(CreateTable(table).compile(dialect=postgresql.dialect()))
        assert 'mkt_' in sql

def test_password_hash():
    h=hash_password('UnitTestPassword-123')
    assert verify_password('UnitTestPassword-123',h)
    assert not verify_password('bad',h)

def test_sitemap_robots(client):
    assert 'https://dialnytics.co.uk' not in client.get('/sitemap.xml').text
    assert 'Disallow: /admin' in client.get('/robots.txt').text
    assert client.get('/healthz').json()['status']=='ok'

def test_email_delivery_job(client,app,monkeypatch):
    from app import mail
    submit(client,request_payload())
    s=app.state.settings;s.smtp_host='smtp.example.invalid';s.mail_from='website@example.org';s.smtp_mode='starttls'
    sent=[]
    class FakeSMTP:
        def __init__(self,*a,**kw): pass
        def starttls(self,**kw): pass
        def login(self,*a): pass
        def send_message(self,message):sent.append(message)
        def __enter__(self):return self
        def __exit__(self,*a):pass
    monkeypatch.setattr(mail.smtplib,'SMTP',FakeSMTP)
    assert mail.deliver_one(app.state.DB,s)
    assert len(sent)==1 and '/admin/requests/' in sent[0].get_content()
    assert 'Please explain the available plans.' not in sent[0].get_content()
    with app.state.DB() as db:assert db.scalar(select(MailJob)).status=='sent'

def test_email_failure_preserves_enquiry(client,app,monkeypatch):
    from app import mail
    submit(client,request_payload())
    s=app.state.settings;s.smtp_host='smtp.example.invalid';s.mail_from='website@example.org'
    def broken(*a,**kw):raise ConnectionError('test failure')
    monkeypatch.setattr(mail.smtplib,'SMTP',broken)
    assert mail.deliver_one(app.state.DB,s)
    with app.state.DB() as db:
        assert db.scalar(select(Submission)) is not None
        job=db.scalar(select(MailJob));assert job.status=='retry';assert job.attempts==1

def test_admin_session_invalidated_on_password_change(client,app):
    login(client)
    app.state.settings.admin_password_hash=hash_password('AnotherTestPassword-1234')
    assert client.get('/admin',follow_redirects=False).status_code==303


def test_admin_pricing_editor(client,app):
    from app.catalog import apply_prices
    try:
        assert client.get('/admin/pricing',follow_redirects=False).status_code==303
        login(client)
        page=client.get('/admin/pricing');assert page.status_code==200 and 'name="usa_per"' in page.text
        import re
        csrf=re.search(r'name="csrf" value="([^"]+)"',page.text).group(1)
        from app.catalog import PRICE_FIELDS,DEFAULT_PRICES
        form={k:str(DEFAULT_PRICES[k]) for k,*_ in PRICE_FIELDS}
        assert client.post('/admin/pricing',data={**form,'usa_per':'20','csrf':'wrong'}).status_code==403
        bad=client.post('/admin/pricing',data={**form,'usa_per':'abc','csrf':csrf});assert bad.status_code==422 and 'Nothing was saved' in bad.text
        ok=client.post('/admin/pricing',data={**form,'usa_per':'20','japan':'59.50','csrf':csrf});assert ok.status_code==200 and 'Prices saved' in ok.text
        assert '$20/user' in client.get('/pricing/').text
        assert '$59.50' in client.get('/numbers/japan/').text
        p=request_payload();p.update(kind='order',phone='+447700900123',plan='usa-canada',users=3,payment='stripe')
        r=submit(client,p);assert r.status_code==200,r.text;assert r.json()['quote']['monthly_total']=='60.00'
        reset=client.post('/admin/pricing',data={**form,'action':'reset','csrf':csrf});assert reset.status_code==200
        assert '$18/user' in client.get('/pricing/').text
    finally:
        apply_prices({})
