"""Durable admin-notification outbox. Failed email never loses the saved enquiry."""
import smtplib, ssl, uuid, logging
from email.message import EmailMessage
from datetime import timedelta
from sqlalchemy import select, update, or_, and_
from .database import MailJob, Submission
from .security import now
log=logging.getLogger(__name__)

def deliver_one(factory, settings):
    if not settings.mail_ready: return False
    current=now()
    due=or_(and_(MailJob.status.in_(['pending','retry']),MailJob.next_attempt<=current),
            and_(MailJob.status=='sending',MailJob.lease_until<current))
    with factory.begin() as db:
        row=db.scalar(select(MailJob).where(due,MailJob.attempts<5).order_by(MailJob.next_attempt).limit(1))
        if not row: return False
        job_id=row.id
        changed=db.execute(update(MailJob).where(MailJob.id==job_id,due).values(status='sending',lease_until=current+timedelta(minutes=5),attempts=MailJob.attempts+1).execution_options(synchronize_session=False))
        if not changed.rowcount: return False
    try:
        with factory() as db:
            job=db.get(MailJob,job_id)
            submission=db.get(Submission,job.submission_id)
            if not submission: return False
            msg=EmailMessage()
            msg['From']=settings.mail_from; msg['To']=settings.mail_to
            msg['Subject']=f'Dialnytics | New {submission.kind} | {submission.reference}'
            msg['Message-ID']=f'<{job_id}@dialnytics.uk>'
            msg.set_content(f'A new {submission.kind} request has been saved.\n\nReference: {submission.reference}\n\nOpen the marketing admin to review customer details:\n{settings.base_url}/admin/requests/{submission.id}\n\nThis notification does not confirm payment, activation or a demo appointment.\nDialnytics Marketing')
        if settings.smtp_mode=='ssl':
            conn=smtplib.SMTP_SSL(settings.smtp_host,settings.smtp_port,timeout=15,context=ssl.create_default_context())
        else:
            conn=smtplib.SMTP(settings.smtp_host,settings.smtp_port,timeout=15)
            conn.starttls(context=ssl.create_default_context())
        with conn:
            if settings.smtp_user: conn.login(settings.smtp_user,settings.smtp_password)
            conn.send_message(msg)
        with factory.begin() as db:
            db.execute(update(MailJob).where(MailJob.id==job_id).values(status='sent',sent_at=now(),lease_until=None,last_error=''))
    except Exception as exc:
        log.warning('Marketing email failed: %s',type(exc).__name__)
        with factory.begin() as db:
            job=db.get(MailJob,job_id)
            if job:
                job.status='failed' if job.attempts>=5 else 'retry'
                job.next_attempt=now()+timedelta(minutes=min(60,2**job.attempts))
                job.lease_until=None
                job.last_error=type(exc).__name__+'; check SMTP configuration and provider delivery logs.'
    return True
