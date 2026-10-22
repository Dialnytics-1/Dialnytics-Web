"""Local setup and deployment helpers. Never contact or migrate the existing dialer."""
import argparse, getpass, os, secrets
from pathlib import Path
from .security import hash_password
from .settings import ROOT

def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('command',choices=['setup','hash-password','init-db','send-emails'])
    args=parser.parse_args()
    if args.command in ('setup','hash-password'):
        if args.command=='setup' and (ROOT/'.env').exists():
            print('.env already exists; it was not changed. Edit it locally or run hash-password to create a replacement hash.')
            return
        password=getpass.getpass('Choose your marketing-admin password (12+ characters): ')
        if password!=getpass.getpass('Repeat password: '): raise SystemExit('Passwords did not match. Nothing was saved.')
        hashed=hash_password(password)
        if args.command=='hash-password': print(hashed);return
        content="\n".join([
            'APP_ENV=development','MARKETING_BASE_URL=http://localhost:8000',
            'MARKETING_DATABASE_URL=sqlite:///./data/marketing.sqlite3',
            'APP_SECRET_KEY='+secrets.token_urlsafe(48),
            'ADMIN_EMAIL=admin@dialnytics.co.uk',"ADMIN_PASSWORD_HASH='"+hashed+"'",
            'NOTIFICATION_EMAIL=admin@dialnytics.co.uk','SMTP_HOST=','SMTP_PORT=587',
            'SMTP_SECURITY=starttls','SMTP_USERNAME=','SMTP_PASSWORD=','MAIL_FROM=',
            'EMAIL_WORKER_ENABLED=true',''])
        (ROOT/'data').mkdir(exist_ok=True)
        (ROOT/'.env').write_text(content,encoding='utf-8')
        try: os.chmod(ROOT/'.env',0o600)
        except OSError: pass
        print('Local .env created. Start with: python -m uvicorn app.main:app --host 127.0.0.1 --port 8000')
        return
    from .settings import Settings
    from .database import make_database,init_database
    settings=Settings();settings.validate();engine,DB=make_database(settings.database_url)
    init_database(engine)
    if args.command=='init-db': print('Marketing tables ready in the configured separate database.')
    else:
        from .mail import deliver_one
        if not settings.mail_ready: raise SystemExit('SMTP not configured. Requests remain saved; no email was sent.')
        sent=0
        while sent<100 and deliver_one(DB,settings): sent+=1
        print(f'Processed {sent} notification jobs. Check admin request details for delivery status.')
    engine.dispose()

if __name__=='__main__': main()
