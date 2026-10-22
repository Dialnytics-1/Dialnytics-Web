# Local QA report

Build: 22 October 2026. Not a production deployment or a security certification.

## Executed checks

- Python compilation and all 20 Jinja templates: passed.
- Backend pytest suite: **47 tests passed**.
- JavaScript pricing suite: **21 assertions passed**.
- JavaScript syntax checks: all six source files passed.
- Public routes: **120** rendered successfully in the backend tests.
- Internal navigation destinations: checked through the local application.
- Browser interaction checks: **8** groups passed.
- Layout matrix: **64** page/width combinations checked, at
  320, 360, 390, 768, 1024, 1280, 1920 and 3840 CSS pixels.
- Final page-level horizontal overflow findings: **0** in this matrix. Wide data
  tables use internal scrolling or mobile cards, not whole-page overflow.
- Browser JavaScript runtime errors in these checks: **0**.

Browser interactions checked:
- Desktop navigation open/Escape
- Mobile navigation and country menu
- Pricing +/- and plan/country switches
- Order full wizard, persistence, reference and WhatsApp handoff
- Demo save and timing-confirmation message
- Contact form save
- Marketing admin displays persisted website submissions
- Guide search and empty-result state

Backend tests include server-authoritative prices, request validation, CSRF/origin
rejection, admin protection, idempotency, saved demo state, email-job creation,
mocked SMTP success/failure, admin notes/status/export/deletion, XSS escaping,
CSV injection protection, credential-change session invalidation and the
separate-database guard. PostgreSQL table DDL compilation was also checked.

## Testing method and limits

The backend used isolated temporary SQLite databases and the local FastAPI HTTP
application. No real customer records or secrets were used. The installed managed
Chromium blocked navigation to local and arbitrary preview hosts; downloading
another browser was unavailable. For visual/interaction QA, server-rendered HTML,
local CSS, images and scripts were loaded into Chromium documents, and form fetches
were bridged to the real local QA HTTP app. This exercises the UI and persistence
logic, but is **not** a real deployed-origin, production-cookie or CSP transport test.
The response security headers were tested separately through the HTTP suite.

A mobile admin-table overflow found during this process was fixed; the final matrix
passed. Representative desktop/mobile screenshots were visually inspected. This is
not a guarantee of perfection on every possible device or browser.

Not performed: real production PostgreSQL/Supabase connection tests; real SMTP inbox
or bounce delivery; live WhatsApp delivery; real payments; live DNS/HTTPS; existing
dialer/Telnyx/Twilio calls; device-specific browser calling behaviour. SMTP success
and failure were tested using mocks only. Follow DEPLOYMENT.md before going live.

Screenshots use explicitly labelled sample/QA data. No QA database or .env secrets
are included in the deliverable.
