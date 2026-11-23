# Send verification codes to ANY email address

Your app already sends the OTP to whatever email the user types at registration.

## Why only one Gmail works today

Resend free / testing mode with `onboarding@resend.dev` only allows sending **to the email you used to sign up at Resend**.

To allow **every** registered user email:

## Option 1 — Verify a domain on Resend (recommended)

1. Buy or use a domain you control (e.g. yourname.com), or a free subdomain service if you have one.
2. Open https://resend.com/domains → Add domain.
3. Add the DNS records Resend shows (SPF, DKIM, etc.) at your DNS provider.
4. Wait until status is **Verified**.
5. In `.env` change the sender to an address on that domain:

```env
EMAIL_PROVIDER=resend
RESEND_API_KEY=re_your_key
MAIL_DEFAULT_SENDER=QSMART Zambia <noreply@yourdomain.com>
```

6. Restart `python app.py`.

After that, OTPs can go to gmail.com, yahoo.com, institutional emails, etc.

## Option 2 — Gmail SMTP (sends to any address)

1. Google Account → Security → 2-Step Verification → App passwords.
2. In `.env`:

```env
EMAIL_PROVIDER=
RESEND_API_KEY=
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USERNAME=poulmalima817@gmail.com
MAIL_PASSWORD=your-16-char-app-password
MAIL_DEFAULT_SENDER=poulmalima817@gmail.com
MAIL_USE_TLS=true
```

3. Restart the app.

Gmail can send to any recipient (daily limits apply).

## App behaviour (already implemented)

- Registration always uses `channel = email`
- Code is emailed to the address on the form
- Code is **not** shown on the website
- Resend / SMTP errors are shown as flash messages
