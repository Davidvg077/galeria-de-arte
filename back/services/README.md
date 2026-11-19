# Gart Gallery microservices

Each service is an independent FastAPI application. The API gateway is the
public entry point and routes requests by domain. Services own separate domain
tables in PostgreSQL and communicate with one another through APIs.

| Service | Port | Responsibility |
| --- | ---: | --- |
| Gallery | 3001 | Galleries and artist-gallery relationships |
| Works | 3002 | Works, availability, prices, and artist/work relationships |
| Auth | 3003 | Users, roles, permissions, login, sessions, and email verification |
| Purchase | 3004 | Carts, price snapshots, confirmation, and pending orders |
| Content | 3005 | Landing page, web pages, artists, and public content |

## API contracts

Every service exposes `GET /health`.

* Auth: `POST /api/auth/login|register`, `GET /api/auth/me`,
  `POST /api/auth/logout`, `PUT /api/auth/email`,
  `POST /api/auth/email/verification/request|confirm`, and
  `POST /api/auth/password/forgot|reset`.
* Gallery: `GET/POST /api/galleries`, `GET /api/galleries/{id}`.
* Works: `GET/POST /api/works`, `GET /api/works/{id}`,
  `PUT/DELETE /api/works/{id}`, and
  `PATCH /api/works/{id}/moderation`. Artist accounts use
  `GET /api/works/mine`, `POST /api/works/submissions`,
  `PUT/DELETE /api/works/{id}/submission`; artists can only manage their own
  works and publish them to the public catalog. Listing supports `q`,
  `category`, `page`, and `limit`.
* Purchase: `GET/PUT/DELETE /api/cart/{user_id}`,
  `POST /api/purchases/checkout` (legacy `POST /api/purchases` is retained)
  with an `Idempotency-Key`, `POST /api/purchases/{checkout_id}/confirm`,
  `POST /api/purchases/{checkout_id}/code`, `GET /api/purchases`, and
  `GET /api/purchases/{id}`.
* Content: `GET /api/content`, `GET /api/content/landing`,
  `GET/POST /api/content/pages`, and `GET /api/artists`.

## Service structure and database

All services use the shared PostgreSQL connection helper in
`back/services/db.py`.
`DATABASE_URL` is mandatory when `ENVIRONMENT=production`. For local
development, the helper reads the root `.env` and has a documented localhost
PostgreSQL default. Each service creates and seeds only its own tables:

| Service | PostgreSQL tables |
| --- | --- |
| Gallery | `gallery_galleries` |
| Works | `works_works` |
| Auth | `auth_users`, `auth_sessions`, `auth_login_attempts`, `auth_email_tokens` |
| Purchase | `purchase_carts`, `purchase_purchases`, `purchase_checkouts`, `purchase_checkout_codes` |
| Content | `content_artists`, `content_pages`, `content_landing` |

Auth and Purchase use `models/` and `controllers/` packages, with schemas and
repositories separated from API handlers. Gallery, Content, and Works use
`models/`, `controllers/`, and `views/` MVC-style packages. The hyphenated
service directories retain small `app.py` entrypoints for Docker, Render, and
existing commands. Database and unexpected failures are logged server-side and
return sanitized responses.

The Astro frontend is in `front/src/` because Astro derives public routes from
`front/src/pages/`. The superseded HTML application, its static assets, data,
and server are grouped under `back/legacy/`; it is not used by the active
`back/api-gateway/server.js` entrypoint.

New passwords use salted PBKDF2-HMAC-SHA256 hashes. Existing plaintext
passwords are upgraded on startup. The known default `admin/admin123` account
is disabled; set `ADMIN_PASSWORD` (at least 12 characters) to provision or
rotate a `WEBMASTER` account. No administrator password is shipped in the
repository. Sessions are opaque, stored as digests, and issued in `HttpOnly`,
`SameSite=Strict` cookies with a 12-hour expiration. Login attempts are
rate-limited.

Configure SMTP with `SMTP_HOST`, `SMTP_PORT`, `SMTP_USER`, `SMTP_PASSWORD`,
and `SMTP_FROM` to enable email verification, password recovery, and purchase
OTPs. Docker Compose uses a local Mailpit inbox by default; open
`http://127.0.0.1:8025/` to read test messages. Disable `SMTP_STARTTLS` only
for trusted local SMTP servers such as Mailpit. Set a random `TOKEN_PEPPER` of
at least 32 characters in production; Docker generates one locally. Email
tokens are short-lived, single-use, stored as digests, and rate-limited.
Accounts without a verified email cannot recover passwords or create purchase
orders.

Purchase APIs derive prices and availability from Works rather than trusting
client-supplied prices, require an authenticated owner, use an idempotency key,
and require an email OTP. Confirmed orders remain `pending_payment`; no
payment provider or card data is configured, so the application does not
charge customers. Configure a payment provider separately before implementing
settlement.

## Local setup

From the repository root, create a virtual environment and install the shared
backend dependencies:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r back\services\requirements.txt
```

Copy `back/.env.example` to `back/.env` and set `DATABASE_URL` to your PostgreSQL
connection string. The database helper loads `back/.env` automatically.
Set the SMTP variables and `ADMIN_PASSWORD` in the environment or an excluded
local `.env` file when needed. Never commit credentials.

Run a service from the repository root:

```powershell
python back\services\auth-service\app.py
```

Initialize all service tables and seed records explicitly:

```powershell
python back\services\init_db.py
```

Or from npm:

```powershell
Push-Location back
npm run db:init
Pop-Location
```

The command is safe to rerun, verifies PostgreSQL, and confirms that every
service table exists.

## Render deployment

The Render Blueprint is in `back/render.yaml`; select that file as the Blueprint
path in the Render dashboard. Its frontend build runs from the repository root
and serves the generated static pages through the backend gateway. Render
supplies `PORT` to each service. Set the
SMTP and administrator secret values in the Render dashboard; without SMTP,
email-dependent actions return an error instead of pretending delivery
succeeded. `COOKIE_SECURE=true` is required for HTTPS production deployments.
