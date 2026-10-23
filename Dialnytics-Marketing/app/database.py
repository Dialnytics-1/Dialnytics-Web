"""Marketing-only storage. Refuses to initialise inside an existing dialer database."""
from datetime import datetime
from sqlalchemy import create_engine, inspect, event, String, Text, DateTime, Integer, Boolean, JSON, ForeignKey, UniqueConstraint, text
from sqlalchemy.orm import DeclarativeBase, mapped_column, Mapped, sessionmaker
from .security import now

class Base(DeclarativeBase): pass
class Submission(Base):
    __tablename__='mkt_submissions'
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    reference: Mapped[str]=mapped_column(String(32),unique=True,index=True)
    idempotency_key: Mapped[str]=mapped_column(String(36),unique=True)
    payload_hash: Mapped[str]=mapped_column(String(64))
    kind: Mapped[str]=mapped_column(String(20),index=True)
    name: Mapped[str]=mapped_column(String(150))
    email: Mapped[str]=mapped_column(String(254),index=True)
    phone: Mapped[str]=mapped_column(String(40),default='')
    company: Mapped[str]=mapped_column(String(200),default='')
    subject: Mapped[str]=mapped_column(String(180),default='')
    message: Mapped[str]=mapped_column(Text,default='')
    details: Mapped[dict]=mapped_column(JSON,default=dict)
    status: Mapped[str]=mapped_column(String(30),default='new',index=True)
    consent_version: Mapped[str]=mapped_column(String(30),default='2026-10-22')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
    updated_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class Note(Base):
    __tablename__='mkt_notes'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    submission_id: Mapped[str]=mapped_column(ForeignKey('mkt_submissions.id',ondelete='CASCADE'),index=True)
    body: Mapped[str]=mapped_column(Text)
    author: Mapped[str]=mapped_column(String(254))
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class AdminSession(Base):
    __tablename__='mkt_admin_sessions'
    token_hash: Mapped[str]=mapped_column(String(64),primary_key=True)
    csrf: Mapped[str]=mapped_column(String(64))
    email: Mapped[str]=mapped_column(String(254))
    credential_tag: Mapped[str]=mapped_column(String(64))
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)
class MailJob(Base):
    __tablename__='mkt_mail_jobs'
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    submission_id: Mapped[str]=mapped_column(ForeignKey('mkt_submissions.id',ondelete='CASCADE'),unique=True)
    status: Mapped[str]=mapped_column(String(20),default='pending',index=True)
    attempts: Mapped[int]=mapped_column(Integer,default=0)
    next_attempt: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
    lease_until: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    sent_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    last_error: Mapped[str]=mapped_column(String(200),default='')
class Audit(Base):
    __tablename__='mkt_audit'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    actor: Mapped[str]=mapped_column(String(254))
    action: Mapped[str]=mapped_column(String(100))
    reference: Mapped[str]=mapped_column(String(32),default='')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class RateBucket(Base):
    __tablename__='mkt_rate_buckets'
    key: Mapped[str]=mapped_column(String(120),primary_key=True)
    count: Mapped[int]=mapped_column(Integer,default=1)
    expires_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),index=True)

class ChatConversation(Base):
    """One website-chat visitor or one WhatsApp number."""
    __tablename__='mkt_chat_conversations'
    id: Mapped[str]=mapped_column(String(36),primary_key=True)
    channel: Mapped[str]=mapped_column(String(12),index=True)          # web | whatsapp
    contact_key: Mapped[str]=mapped_column(String(90),unique=True)     # wa:+447... | web:<hash>
    phone: Mapped[str]=mapped_column(String(40),default='')
    display_name: Mapped[str]=mapped_column(String(150),default='')
    language: Mapped[str]=mapped_column(String(8),default='')
    ai_enabled: Mapped[bool]=mapped_column(Boolean,default=True)
    needs_human: Mapped[bool]=mapped_column(Boolean,default=False)
    unread: Mapped[int]=mapped_column(Integer,default=0)
    ai_replies: Mapped[int]=mapped_column(Integer,default=0)
    lead: Mapped[dict]=mapped_column(JSON,default=dict)
    lead_id: Mapped[str | None]=mapped_column(ForeignKey('mkt_submissions.id',ondelete='SET NULL'),nullable=True,index=True)
    last_preview: Mapped[str]=mapped_column(String(200),default='')
    last_inbound_at: Mapped[datetime | None]=mapped_column(DateTime(timezone=True),nullable=True)
    last_message_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now)
class ChatMessage(Base):
    __tablename__='mkt_chat_messages'
    id: Mapped[int]=mapped_column(Integer,primary_key=True,autoincrement=True)
    conversation_id: Mapped[str]=mapped_column(ForeignKey('mkt_chat_conversations.id',ondelete='CASCADE'),index=True)
    role: Mapped[str]=mapped_column(String(12))                         # user | assistant | admin | system
    body: Mapped[str]=mapped_column(Text,default='')
    provider_id: Mapped[str | None]=mapped_column(String(100),unique=True,nullable=True)
    status: Mapped[str]=mapped_column(String(20),default='')
    created_at: Mapped[datetime]=mapped_column(DateTime(timezone=True),default=now,index=True)

def make_database(url):
    if url.startswith('postgres://'): url=url.replace('postgres://','postgresql+psycopg://',1)
    elif url.startswith('postgresql://'): url=url.replace('postgresql://','postgresql+psycopg://',1)
    sqlite=url.startswith('sqlite')
    options={'pool_pre_ping':True}
    if sqlite: options['connect_args']={'check_same_thread':False,'timeout':15}
    else: options.update(pool_size=5,max_overflow=3,pool_timeout=15,connect_args={'connect_timeout':10})
    engine=create_engine(url,**options)
    if sqlite:
        @event.listens_for(engine,'connect')
        def sqlite_setup(conn, _):
            conn.execute('PRAGMA foreign_keys=ON')
            conn.execute('PRAGMA journal_mode=WAL')
    return engine, sessionmaker(engine,expire_on_commit=False)

def init_database(engine):
    existing=set(inspect(engine).get_table_names())
    if existing & {'dialnytics_users','caller_id_assignments','power_queues'}:
        raise RuntimeError('Existing dialer tables detected. Use a NEW separate marketing database/project, not the dialer database.')
    Base.metadata.create_all(engine)
    if engine.dialect.name=='postgresql':
        with engine.begin() as conn:
            for table in Base.metadata.tables:
                conn.execute(text(f'ALTER TABLE "{table}" ENABLE ROW LEVEL SECURITY'))
                # The server must connect as the table owner (not Supabase anon/authenticated).
                for role in ('anon','authenticated'):
                    if conn.execute(text('SELECT 1 FROM pg_roles WHERE rolname=:r'),{'r':role}).first():
                        conn.execute(text(f'REVOKE ALL ON TABLE "{table}" FROM "{role}"'))
