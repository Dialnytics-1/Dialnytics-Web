from dataclasses import dataclass, field
from pathlib import Path
import os
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent.parent
load_dotenv(ROOT / '.env', override=False)

@dataclass
class Settings:
    env: str = field(default_factory=lambda: os.getenv('APP_ENV','development'))
    base_url: str = field(default_factory=lambda: os.getenv('MARKETING_BASE_URL','http://localhost:8000').rstrip('/'))
    database_url: str = field(default_factory=lambda: os.getenv('MARKETING_DATABASE_URL',f'sqlite:///{ROOT / "data" / "marketing.sqlite3"}'))
    secret: str = field(default_factory=lambda: os.getenv('APP_SECRET_KEY',''))
    admin_email: str = field(default_factory=lambda: os.getenv('ADMIN_EMAIL','admin@dialnytics.co.uk').strip().lower())
    admin_password_hash: str = field(default_factory=lambda: os.getenv('ADMIN_PASSWORD_HASH',''))
    smtp_host: str = field(default_factory=lambda: os.getenv('SMTP_HOST',''))
    smtp_port: int = field(default_factory=lambda: int(os.getenv('SMTP_PORT','587')))
    smtp_user: str = field(default_factory=lambda: os.getenv('SMTP_USERNAME',''))
    smtp_password: str = field(default_factory=lambda: os.getenv('SMTP_PASSWORD',''))
    smtp_mode: str = field(default_factory=lambda: os.getenv('SMTP_SECURITY','starttls'))
    mail_from: str = field(default_factory=lambda: os.getenv('MAIL_FROM',''))
    mail_to: str = field(default_factory=lambda: os.getenv('NOTIFICATION_EMAIL','admin@dialnytics.co.uk'))
    worker: bool = field(default_factory=lambda: os.getenv('EMAIL_WORKER_ENABLED','true').lower() == 'true')
    # AI customer-service assistant (website chat + WhatsApp)
    anthropic_key: str = field(default_factory=lambda: os.getenv('ANTHROPIC_API_KEY','').strip())
    ai_model: str = field(default_factory=lambda: os.getenv('AI_MODEL','claude-haiku-5-5').strip())
    chat_enabled: bool = field(default_factory=lambda: os.getenv('CHAT_WIDGET_ENABLED','true').lower() == 'true')
    telnyx_key: str = field(default_factory=lambda: os.getenv('TELNYX_API_KEY','').strip())
    telnyx_public_key: str = field(default_factory=lambda: os.getenv('TELNYX_PUBLIC_KEY','').strip())
    wa_from: str = field(default_factory=lambda: os.getenv('WHATSAPP_FROM_NUMBER','+447476629105').strip())
    wa_profile_id: str = field(default_factory=lambda: os.getenv('TELNYX_MESSAGING_PROFILE_ID','').strip())
    wa_ai_default: bool = field(default_factory=lambda: os.getenv('WHATSAPP_AI_DEFAULT','true').lower() == 'true')
    admin_whatsapp: str = field(default_factory=lambda: os.getenv('ADMIN_WHATSAPP_NUMBER','').strip())
    wa_alert_template: str = field(default_factory=lambda: os.getenv('WHATSAPP_ALERT_TEMPLATE','').strip())
    wa_alert_lang: str = field(default_factory=lambda: os.getenv('WHATSAPP_ALERT_TEMPLATE_LANG','en').strip())
    # Card checkout (Stripe). Off unless both are set. Never expose these to the browser.
    stripe_secret_key: str = field(default_factory=lambda: os.getenv('STRIPE_SECRET_KEY','').strip())
    stripe_webhook_secret: str = field(default_factory=lambda: os.getenv('STRIPE_WEBHOOK_SECRET','').strip())
    @property
    def stripe_ready(self): return self.stripe_secret_key.startswith(('sk_live_','sk_test_','rk_live_','rk_test_')) and self.stripe_webhook_secret.startswith('whsec_')
    @property
    def ai_ready(self): return bool(self.anthropic_key)
    @property
    def whatsapp_ready(self): return bool(self.telnyx_key and self.telnyx_public_key and self.wa_from)
    @property
    def production(self): return self.env == 'production'
    @property
    def mail_ready(self): return bool(self.smtp_host and self.mail_from and self.mail_to)
    def validate(self):
        if len(self.secret) < 32:
            raise RuntimeError('Run python -m app.manage setup, or set APP_SECRET_KEY to a random 32+ character secret.')
        if not self.admin_password_hash.startswith('scrypt$'):
            raise RuntimeError('ADMIN_PASSWORD_HASH is required. Generate it with python -m app.manage hash-password.')
        if self.production and not self.base_url.startswith('https://'):
            raise RuntimeError('Production MARKETING_BASE_URL must use HTTPS.')
        if self.production and not self.database_url.startswith(('postgres://','postgresql://','postgresql+psycopg://')):
            raise RuntimeError('Production requires a separate PostgreSQL MARKETING_DATABASE_URL; local SQLite is for development only.')
        if self.smtp_mode not in ('starttls','ssl'):
            raise RuntimeError('SMTP_SECURITY must be starttls or ssl. Plaintext SMTP is not supported.')
