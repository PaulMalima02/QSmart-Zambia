# QSMART Zambia

Smart queue management for Zambian banks, hospitals and government services.

## Stack
Flask · SQLite (Postgres-ready) · Bootstrap 5 · Leaflet · Flask-Login  
SMS: local log gateway · Africa's Talking · Twilio  
Email: SMTP · Resend  
OTP: hashed, rate-limited, 5-attempt lockout, 60s resend cooldown

## Setup
```bash
cd qsmart_zambia
python -m venv venv
source venv/bin/activate   # Windows: venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env
python app.py
```
Open http://localhost:5000

## Default accounts (after seed)
| Role     | Username | Password  |
|----------|----------|-----------|
| Admin    | admin    | Admin123! |
| Customer | demo     | Demo123!  |

Admin is created only from environment variables — **not** public registration.  
Staff must register, select an institution, then be **approved by admin**.

## Key flows
1. Customer registers → choose SMS or email OTP → verify → join queue / send query  
2. Staff registers → verify → pending → admin approves → manage queue & reply to queries  
3. Completing a ticket notifies the next customer (in-app + SMS when configured)  
4. Forgot password → reset link by email (or on-screen in local mode)

---

## SMS configuration

### 1. Local gateway (default — no keys needed)

```env
SMS_PROVIDER=log
SMS_API_KEY=
```

- Messages are printed in the terminal: `[SMS:log] To:+260... Msg:...`
- OTP codes appear on the **Verify** page and as `[QSMART OTP] ...`
- Rows are stored in `sms_log` with status `log_only`
- Perfect for development and demos

### 2. Africa's Talking (recommended for Zambia +260)

**Sandbox (test):**
```env
SMS_PROVIDER=africastalking
SMS_API_KEY=your_sandbox_api_key
SMS_USERNAME=sandbox
SMS_SENDER=QSMART
```

**Live:**
```env
SMS_PROVIDER=africastalking
SMS_API_KEY=your_live_api_key
SMS_USERNAME=your_live_username
SMS_SENDER=QSMART
```

Sign up: https://africastalking.com — use Sandbox first, then upgrade.

### 3. Twilio

```env
SMS_PROVIDER=twilio
SMS_API_KEY=ACCOUNT_SID:AUTH_TOKEN
SMS_FROM_NUMBER=+1XXXXXXXXXX
SMS_SENDER=QSMART
```

`SMS_API_KEY` must be `SID:TOKEN` (colon-separated). Trial accounts only send to verified numbers.

### Phone numbers
Prefer E.164. The app normalizes:
- `097XXXXXXX` → `+26097XXXXXXX`
- `26097XXXXXXX` → `+26097XXXXXXX`
- `+26097XXXXXXX` → unchanged

---

## Email configuration (optional)

**Local log:** leave `MAIL_SERVER` and `RESEND_API_KEY` empty.  
**SMTP / MailHog:** set `MAIL_SERVER`, `MAIL_PORT`, etc.  
**Resend:** `EMAIL_PROVIDER=resend` + `RESEND_API_KEY`.

---

## OTP security
| Setting                      | Default |
|-----------------------------|---------|
| Expiry                      | 5 min   |
| Max verification attempts   | 5       |
| Resend cooldown             | 60 s    |
| Storage                     | hashed (scrypt), never plain text |

---

## Environment variables
See `.env.example` for the full list (SMS, email, OTP, admin seed, retention).

---

## Mobile access — Android & iPhone

QSMART is a **Progressive Web App**. Users install it from the browser onto the home screen (works on **Android and iPhone**). No Play Store / App Store listing is required for this mode.

### Install on a phone

1. Open the site **on the phone** (not desktop).
2. Prefer **HTTPS** (or use ngrok for testing — see below).
3. Go to **/install** for step-by-step instructions, or:
   - **Android (Chrome):** menu ⋮ → **Install app** / **Add to Home screen**
   - **iPhone (Safari only):** Share → **Add to Home Screen**

A banner also appears on mobile with the correct steps for each platform.

### Why install may only show on desktop

Browsers only offer the one-tap **Install** button when:
- The site is on **HTTPS** (or `localhost`), and
- A valid **manifest** + **service worker** are present.

`http://192.168.x.x:5000` on a phone often **blocks** the install prompt. Fixes:

```bash
# Quick public HTTPS tunnel (test on any phone, any network)
ngrok http 5000
# Open the https://….ngrok-free.app URL on the phone → Install / Add to Home Screen
```

Or deploy to Railway / Render / Fly.io (HTTPS included).

### Searchable on the web

| Platform | How |
|----------|-----|
| Google / Bing | Deploy on a public HTTPS domain → submit `/sitemap.xml` in Search Console |
| WhatsApp / social | Open Graph tags already set |
| Play Store | Optional later: wrap PWA as TWA (Bubblewrap) or Capacitor |
| App Store | Optional later: Capacitor/Ionic wrapper + Apple developer account |

The free path (PWA + Google search) covers most users without app-store fees.

### Get the app page

`/install` — dedicated guide for Android and iPhone, linked from the home page as **Get the app**.

---

## Deploy (permanent HTTPS for phones & search)

You need a public **https://** URL so Android/iPhone can Install / Add to Home Screen, and so Google can index the site.

### Option A — Render (recommended, free tier)

1. Push this folder to a **GitHub** repository.
2. Go to [https://render.com](https://render.com) → **New** → **Blueprint**.
3. Connect the repo. Render reads `render.yaml`.
4. Set **ADMIN_PASSWORD** when prompted (required).
5. Deploy. You get a URL like `https://qsmart-zambia.onrender.com`.

Open that URL **on your phone** → **/install** → Add to Home Screen.

**Environment variables** (set in Render dashboard if needed):

| Variable | Example |
|----------|---------|
| `SECRET_KEY` | auto-generated by blueprint |
| `ADMIN_PASSWORD` | your strong password |
| `SMS_PROVIDER` | `log` or `africastalking` / `twilio` |
| `DATABASE_URL` | auto from Render Postgres |

Free web services on Render **sleep** after idle; first request may take ~30s.

### Option B — Railway

1. [railway.app](https://railway.app) → New Project → Deploy from GitHub.
2. Add a **PostgreSQL** plugin; Railway sets `DATABASE_URL`.
3. Set env: `SECRET_KEY`, `FLASK_ENV=production`, `FORCE_HTTPS=true`, `ADMIN_PASSWORD`, …
4. Start command is already in `railway.toml` / `Procfile`.

### Option C — Quick test tunnel (no account)

```bash
python app.py
# other terminal:
ngrok http 5000
```

Share the `https://….ngrok-free.app` link. Good for testing install on phones; not permanent.

### After deploy

1. Open `https://your-app…/install` on Android and iPhone and install.
2. In [Google Search Console](https://search.google.com/search-console), add the property and submit `https://your-app…/sitemap.xml`.
3. Optionally set real SMS/email keys for production OTP delivery.

---

## Email & SMS live setup

See **[SETUP_EMAIL_SMS.md](SETUP_EMAIL_SMS.md)** for Resend, SMTP, and Africa's Talking (sandbox + live).

Check config:
```bash
python scripts/check_providers.py
```


## Deploy on Render

See **[DEPLOY_RENDER.md](DEPLOY_RENDER.md)** for step-by-step GitHub + Render Blueprint deploy (HTTPS for Android & iPhone).

