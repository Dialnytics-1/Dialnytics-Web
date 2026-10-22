# Dialnytics - Complete Marketing Website

A separate, multi-page marketing application for **dialnytics.uk**, with its own
forms database, marketing admin and email-notification outbox.

**Do not upload this project over the working dialer repository or Render service.**
The existing dialer stays at **https://dialnytics.co.uk**. This app contains no
Telnyx/Twilio credentials and does not create or modify dialer accounts.

## Start here

- Website: `https://dialnytics.uk`
- Marketing admin: `https://dialnytics.uk/admin`
- Admin email: `admin@dialnytics.co.uk`
- Client Login: `https://dialnytics.co.uk`
- WhatsApp: `+44 7476 629105`
- Contact email: `admin@dialnytics.co.uk`
- No password, API keys, database connection strings or SMTP passwords are included.

### Windows / local preview

1. Extract the ZIP into a normal writable folder, for example:
   `%USERPROFILE%\Documents\Dialnytics-Marketing`.
2. Install Python 3.11 or newer with the Python Launcher if needed.
3. Double-click **START_WINDOWS.bat**. It creates a local virtual environment and
   installs the dependencies. On first run it asks you to choose your own admin
   password (at least 12 characters).
4. Open `http://localhost:8000` for the website and
   `http://localhost:8000/admin` for the marketing admin.
5. Sign in with `admin@dialnytics.co.uk` and the password you chose.

**This is a backend application, not two standalone HTML files.** Do not double-click
Jinja templates or run them directly using VS Code F5. Node.js is not needed to run
this website. The local server must remain running while you use it.

For macOS/Linux: run `./start-local.sh` from a terminal. Manual startup:

```sh
python -m venv .venv
# Activate the virtual environment using the command for your operating system.
python -m pip install -r requirements.txt
python -m app.manage setup
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Local development uses `data/marketing.sqlite3`. It is separate from the dialer.
No sample enquiries are inserted. No default admin password exists.

## Production deployment

See **docs/DEPLOYMENT.md**. You need a **NEW** PostgreSQL/Supabase database/project,
a **NEW** Render web service (or equivalent Python host) and real SMTP credentials.
Do not reuse the dialer's database or change its domain settings.

Production deliberately refuses SQLite. The application also refuses initialisation
when known Dialnytics dialer tables are found in the configured database. Only its
`mkt_*` tables are created; no existing dialer migration is needed.

An enquiry is saved in the database before a reference and WhatsApp handoff are
shown. Email delivery is queued separately. Missing/failed SMTP does not discard
the request or pretend that an email was sent; the admin shows notification status.

## Included public website

- Original navy, white and purple design; fluid layouts and accessible navigation.
- Home, pricing, live calculator and country pages.
- Multi-step requests for every plan: Plan -> Included -> Details -> Review -> Done.
- Server-validated prices and idempotent request saving.
- Product overview, feature pages, illustrative interactive tour and availability pages.
- 24 solution/industry pages with original workflow copy.
- Help centre, original practical guides, FAQs, browser guide and website search.
- About, payments, contact, support, custom quotes and 15-minute demo request forms.
- Policy pages, sitemap, robots, metadata and social image.
- No Refer & Earn, affiliate portal, invented testimonials or fake customer video.
- Unavailable features are not sold as current features. SMS/voicemail are explicitly
  unavailable; AI summaries/transcripts, live captions and Floating Phone are on a
  clearly labelled roadmap without an invented launch date.

See **docs/PAGES.md** for the actual route list. There are shared templates rather
than 100 copies of identical HTML. Every listed route resolves through this app.
Reference-like information architecture does not mean copied source, private
backend access, or copied customer media.

## Separate marketing admin

- Authenticated inbox for order, contact, quote, demo and support submissions.
- Search, type/status filters, pagination and filtered CSV export.
- Customer details, request snapshot, status changes and internal notes.
- Status values: New, Contacted, Awaiting Payment, Paid, Demo Confirmed, Closed, Spam.
- Email-notification status, retries and administrative audit events.
- Confirmed deletion of a request and its notes/email job.
- Server-side sessions, CSRF checks, login throttling and safe CSV export.
- **Marking Paid is an internal workflow action. It does not charge a card or
  activate a dialer. Demo Confirmed does not send an automatic WhatsApp message.**

## Confirmed commercial settings

| Plan | Monthly USD |
|---|---:|
| USA/Canada, one user | $22 |
| USA/Canada, two users | $38 total |
| USA/Canada, three or more | $15 per user |
| UK | $29 per user |
| Australia | $44 per user |
| Japan | $64 per user |
| Global | $179 per user |
| UK to Europe, one selected destination | $44 per user |
| European local numbers / Custom | Quote before payment |

No setup fee, no extra plan charges and no free trial. The seven confirmed included
features are unlimited calling, dedicated caller ID, CRM integration, Power Dialer,
Call Logs & Analytics, incoming/outgoing calling and call recording.

See **docs/PRICING.md** for UK-to-Europe multi-destination totals and the rate rule.

- Support: **Monday-Friday, 3 PM to 3 AM next morning, PKT (UTC+5)**.
  Friday's support shift ends Saturday at 3 AM.
- Activation: **24/7, 10-15 minutes after payment confirmation**.
- Demo: **15 minutes**. The customer receives this success message:
  "We will send you a WhatsApp message to confirm the date and time of your 15-minute demo."
- Bank Transfer, USDT and Stripe card payments are **preferences for manual payment
  arrangements**, not a live checkout. No payment provider key is needed for this
  manual enquiry workflow.

## Publication items requiring the operator's review

1. Refund/cancellation terms were intentionally left undecided by the owner. The
   public billing page says to request the applicable written terms before paying.
   Review the original policy drafts, privacy/retention arrangements and terms before
   publication. No automatic refund/no-refund rule was invented.
2. The PRIME MSM LIMITED legal name, company number **17282032** and registered office
   are owner-supplied. The live company detail page was not retrievable during this
   build. Verify current registration details and the genuine operating relationship
   before publication. Registered office is not described as a walk-in operating office.
3. The owner specified no fixed monthly minute cap. The pages distinguish included
   destinations from every possible network/number type. Confirm actual destination
   coverage, number inventory and recording retention with your operational providers.
4. Website forms cannot make SMTP deliver, configure DNS, purchase numbers or satisfy
   telecom verification automatically. Complete and test the separate deployment.
5. The UK-to-Europe multi-country discount follows the previously described rule of
   USD 1 less per user's monthly package. Review it before publishing multi-country prices.

## Testing

See **docs/QA_REPORT.md**. Local automated tests and UI checks were performed.
They do not establish that live DNS, a new production PostgreSQL database, SMTP
mailbox delivery, WhatsApp delivery or the existing dialer works.

```sh
python -m pip install -r requirements-dev.txt
python -m pytest tests/test_application.py -q
node tests/pricing.mjs
```

## Where to change things

- `app/catalog.py`: prices, country configuration and contact/business details.
- `app/content.py`: original public page copy, solution pages, guides and policies.
- `templates/`: layouts, order form, marketing pages and admin UI.
- `static/css/`: responsive public/admin design.
- `static/js/`: navigation, price calculator, order wizard and enquiry submission.
- `app/main.py`: routes, authentication, request saving and admin workflows.
- `app/database.py`: marketing-only schema and database separation guard.
- `app/mail.py`: durable SMTP notification worker.

Keep `.env`, database files, credentials and customer data out of Git and public ZIPs.
