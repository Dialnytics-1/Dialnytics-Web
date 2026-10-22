# Security and data boundaries

## Implemented

- Separate marketing database/environment variable and a guard against recognised dialer tables.
- No telephony keys, dialer database access, account provisioning or automatic payment processing.
- Server-side scrypt password hashing, random session tokens stored as hashes,
  HttpOnly/SameSite session cookies and Secure cookies in production.
- Admin sessions expire after eight hours and are invalidated by a password-hash change.
- CSRF checks and origin checks for state-changing actions, including login and deletion.
- Public signed form tokens, honeypot, 64 KB request-body limit and input validation.
- Database-backed rate buckets for public submissions and login attempts.
- Idempotent request saving and a transactional notification outbox.
- SQLAlchemy bound queries; Jinja HTML escaping; no customer input used as executable HTML.
- Private admin endpoints, no-index headers and server-side permission checks.
- CSV formula-prefix protection and explicit confirmation for request deletion.
- Production HTTPS setting, CSP, frame protections, no third-party executable CDN assets.
- PostgreSQL RLS and removal of anon/authenticated table privileges where those roles exist.
- Notification emails do not contain full customer messages.

## Required operating controls

Use strong unique admin credentials, restrict infrastructure access, maintain
backups, apply dependency/security updates and configure a verified SMTP sender.
Use TLS for the PostgreSQL connection (`sslmode=require` or stronger), and an
appropriate application database owner/service role. Do not expose that connection
to browsers. The production service must have dependable uptime for submissions
and the email worker to run.

Confirm trusted reverse-proxy configuration with the host. Rate limits are based on
the client address delivered to the app; do not blindly trust arbitrary forwarded
headers from the internet. Shared IPs can share a rate bucket.

There is one marketing admin account in this version, as configured by ADMIN_EMAIL.
Use hosting-level access controls and an MFA-enabled infrastructure account. This
version does not claim an application-level MFA implementation or a security audit.

Keep personally identifiable information only as needed for the actual business
process and applicable record-keeping duties. Configure and approve a retention
schedule. The request deletion workflow is provided; automatic destructive
retention cleanup was not silently enabled.

A database backup, infrastructure security, mail delivery, privacy compliance and
telecom authorisation cannot be established by application code alone.
