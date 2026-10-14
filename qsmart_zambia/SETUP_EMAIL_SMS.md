# Email & SMS setup — QSMART Zambia

This guide configures **live email** (Resend or SMTP) and **Africa’s Talking SMS** (sandbox or live) for OTP and password reset.

---

## 1. Email — Resend (recommended)

Resend is a single API key and works well for OTP + password-reset links.

### Steps

1. Create an account at [https://resend.com](https://resend.com).
2. **API Keys** → Create API key → copy `re_…`.
3. **Domains** → add and verify your domain (or use Resend’s onboarding domain for tests).
4. In `.env`:

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_xxxxxxxxxxxxxxxxxxxxxxxxxxxx
MAIL_DEFAULT_SENDER=QSMART Zambia <noreply@yourdomain.com>
```

5. Restart the app: `python app.py`
6. Register with **Verify via → Email**, or use **Forgot password**.

If the key is wrong, the terminal shows `resend error: …` and OTP still appears on-screen in development.

### Alternative — SMTP (Gmail, MailHog, etc.)

```env
EMAIL_PROVIDER=
RESEND_API_KEY=
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=you@gmail.com
MAIL_PASSWORD=your-app-password
MAIL_DEFAULT_SENDER=you@gmail.com
MAIL_USE_TLS=true
```

Gmail requires an [App Password](https://myaccount.google.com/apppasswords), not your normal password.

**Local test inbox (MailHog):**

```bash
docker run -d -p 1025:1025 -p 8025:8025 mailhog/mailhog
```

```env
MAIL_SERVER=127.0.0.1
MAIL_PORT=1025
MAIL_USE_TLS=false
MAIL_USERNAME=
MAIL_PASSWORD=
```

Open http://localhost:8025 to read messages.

---

## 2. SMS — Africa’s Talking (Zambia +260)

### Sandbox (free testing)

1. Sign up at [https://account.africastalking.com](https://account.africastalking.com).
2. Open **Sandbox** → copy **API Key**.
3. Username is usually `sandbox`.
4. In the sandbox, add a test phone number if required by AT.
5. In `.env`:

```env
SMS_PROVIDER=africastalking
SMS_API_KEY=your_sandbox_api_key_here
SMS_USERNAME=sandbox
SMS_SENDER=QSMART
```

6. Restart the app.
7. Register with phone `+26097XXXXXXX` (or `097XXXXXXX`) and **Verify via → SMS**.

Sandbox messages appear in the **Africa’s Talking dashboard** (not always on a real handset until you go live).

### Live production

1. Create a **live** app in Africa’s Talking (not sandbox).
2. Use the live **API Key** and your live **username**.
3. Register an alphanumeric sender ID / short code if required for Zambia.
4. Same env vars, with live credentials:

```env
SMS_PROVIDER=africastalking
SMS_API_KEY=your_live_api_key
SMS_USERNAME=your_live_username
SMS_SENDER=QSMART
```

### Twilio (optional alternative)

```env
SMS_PROVIDER=twilio
SMS_API_KEY=ACCOUNT_SID:AUTH_TOKEN
SMS_FROM_NUMBER=+1XXXXXXXXXX
```

---

## 3. Recommended `.env` for both

```env
# SMS — Africa's Talking sandbox
SMS_PROVIDER=africastalking
SMS_API_KEY=paste_at_api_key
SMS_USERNAME=sandbox
SMS_SENDER=QSMART

# Email — Resend
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_paste_key
MAIL_DEFAULT_SENDER=QSMART Zambia <onboarding@resend.dev>
```

(`onboarding@resend.dev` works for Resend test sends to your own signup email.)

---

## 4. Verify configuration

```bash
cd qsmart_zambia
python scripts/check_providers.py
```

This prints whether SMS and email providers look configured (does not send a real message unless you pass `--send`).

Or register a test user:

1. Choose **SMS** → check terminal / AT dashboard / phone.  
2. Choose **Email** → check inbox (and spam).  
3. If delivery fails, the **verify page still shows the code** when providers are offline or misconfigured.

---

## 5. Production checklist

| Item | Action |
|------|--------|
| `SECRET_KEY` | Long random string |
| `FLASK_ENV` | `production` |
| `FORCE_HTTPS` | `true` on Render/Railway |
| SMS | Live AT credentials (not sandbox) |
| Email | Resend domain verified |
| Admin password | Strong, only via env |

OTP security (hashing, 5 attempts, 60s resend, 5‑min expiry) works the same in local and live modes.
