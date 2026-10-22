# Deploy independently - never replace the dialer

## 1. New repository and new web service

Create a NEW private repository for the contents of this project folder. Create a NEW
Render Python web service from it. Do not replace the existing Dialnytics dialer
repository, server, environment variables or `dialnytics.co.uk` DNS records.

- Build command: `pip install -r requirements.txt`
- Start command: `uvicorn app.main:app --host 0.0.0.0 --port $PORT --workers 1`
- Health-check path: `/healthz`
- An optional `render.yaml` blueprint is included.
- Choose hosting appropriate for continuous availability. Sleeping/free hosting can
  delay responses and notification processing. Check the host's current costs.
- The included Render configuration uses Python 3.11. Local automated checks ran on
  Python 3.13.5; run the provided tests again on your selected deployment runtime.

## 2. New marketing database

Create a NEW Supabase/PostgreSQL project solely for the marketing website.
Use its direct or supported session-pooler PostgreSQL connection string in:

```
MARKETING_DATABASE_URL=postgresql+psycopg://USER:URL_ENCODED_PASSWORD@HOST:PORT/postgres?sslmode=require
```

Use the host/port from your own project's Connect dialog. URL-encode special password
characters. Do not put this URL in browser JavaScript or commit it to Git.

The server connects using a database owner account and creates only `mkt_*` tables.
On PostgreSQL it enables row-level security on them and revokes table access from
Supabase's `anon` and `authenticated` roles if present. This app never uses the
Supabase public browser API or anonymous key. A database user that does not own these
tables will need deliberately configured privileges/policies; do not simply disable RLS.

Startup stops if it detects `dialnytics_users`, `caller_id_assignments` or
`power_queues` in the selected database. This protects against accidentally using
the existing dialer database. Never bypass the guard to share the dialer database.

Schema creation is automatic. To initialise explicitly:

```
python -m app.manage init-db
```

Do not run old dialer migrations or delete existing number assignments.
Back up the separate production database using your provider's backup facilities.

## 3. Environment variables

| Variable | Value / purpose |
|---|---|
| APP_ENV | `production` |
| MARKETING_BASE_URL | `https://dialnytics.uk` |
| MARKETING_DATABASE_URL | New marketing PostgreSQL connection, TLS required |
| APP_SECRET_KEY | Random secret, at least 32 characters |
| ADMIN_EMAIL | `admin@dialnytics.co.uk` |
| ADMIN_PASSWORD_HASH | Generated scrypt password hash |
| NOTIFICATION_EMAIL | `admin@dialnytics.co.uk` |
| SMTP_HOST | Your authorised SMTP provider hostname |
| SMTP_PORT | `587` for STARTTLS, or `465` for implicit TLS |
| SMTP_SECURITY | `starttls` or `ssl` |
| SMTP_USERNAME | Provider username |
| SMTP_PASSWORD | Provider/app password |
| MAIL_FROM | Sender address approved by your SMTP provider |
| EMAIL_WORKER_ENABLED | `true` |

Generate the app secret locally:

```
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate the admin password hash locally:

```
python -m app.manage hash-password
```

The command asks for the password privately and prints only the hash. Paste the full
hash into the Render value field without additional quotation marks. Never use the
test-suite password for production. Changing this hash invalidates existing admin
sessions. There is no publicly accessible password-reset or default-password endpoint.

## 4. Domain

Add **dialnytics.uk** as a custom domain on the NEW marketing service. Use the exact
DNS instructions Render displays for that service, then verify HTTPS.

- Website: `https://dialnytics.uk`
- Admin: `https://dialnytics.uk/admin`
- Existing dialer link: `https://dialnytics.co.uk`

Do not change the existing dialer's domain, routing, Telnyx settings or database.
Do not point `dialnytics.co.uk/admin` at this project: that was superseded by the
owner's confirmed separate `dialnytics.uk/admin` address.

## 5. Email notifications

Configure a real SMTP sender. The sender domain may need the provider's SPF/DKIM
verification. Do not invent records or overwrite unrelated mail DNS entries.

A saved request creates a durable email job in the same transaction. The worker
checks for jobs every 15 seconds while the app is running. Failed sends are retried
with increasing delays up to five attempts. Failure remains visible in the admin,
where an authorised user can explicitly queue another attempt.

Notifications contain the request type/reference and an authenticated admin link,
not the complete form contents. SMTP acceptance is not proof of inbox delivery.
Inspect your mail provider's delivery/bounce logs as well. Outbox processing is
at-least-once; a crash after SMTP acceptance may cause a duplicate notification, but
not a duplicate website request. An admin can inspect the reference to recognise it.

## 6. Pre-launch verification

1. Check `/healthz` returns OK on the real domain.
2. Visit every menu on desktop and mobile, including keyboard navigation.
3. Submit a contact enquiry; confirm the reference and that it appears in the admin.
4. Confirm the email notification arrives at the real mailbox.
5. Request a demo; confirm timing is pending and the text is correct.
6. Test USA/Canada pricing at 1, 2 and 3 users, and other country plans.
7. Submit a plan enquiry; check server-calculated price, WhatsApp message and reference.
8. Confirm no payment is taken and no dialer account is created automatically.
9. Sign in/out of the admin; test filters, notes, status, CSV export and email retry.
10. Review legal copy, company details, coverage and unpublished refund policy before
    taking real payments. These templates are not a legal/compliance certification.

## Troubleshooting

- `.env` missing / secret error: run local setup or configure production variables.
- Cannot create folders: extract into your own writable Documents directory.
- Email banner says not configured: forms still save; set SMTP and sender variables.
- Database connection error: check NEW project's connection URL, TLS and networking.
- Request reports an expired form: refresh and retry. Forms expire after two hours.
- Do not clear or remove uniqueness/security constraints in response to an error.
- Failed API save does not produce a success screen. Preserve the error and reference
  (if any) before retrying; identical retry keys prevent duplicate submissions.
