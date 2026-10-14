# Production go-live checklist — QSMART Zambia

## 1. Secrets & config
- [ ] `SECRET_KEY` set to a long random value (not the default)
- [ ] `ADMIN_PASSWORD` strong; change after first login
- [ ] `FLASK_ENV=production` and `FORCE_HTTPS=true`
- [ ] `DATABASE_URL` points to managed Postgres (Render/Railway)

## 2. SMS (Africa's Talking)
- [ ] Sandbox tested with `python scripts/check_providers.py`
- [ ] Live app API key + username set
- [ ] `SMS_PROVIDER=africastalking`
- [ ] Test OTP to a real +260 number

## 3. Email (Resend or SMTP)
- [ ] `EMAIL_PROVIDER=resend` + `RESEND_API_KEY=re_…`
- [ ] Domain verified in Resend (or SMTP credentials)
- [ ] Test OTP email + forgot-password link

## 4. Hosting (HTTPS)
- [ ] Deployed on Render Blueprint or Railway
- [ ] `https://…/health` returns `{"status":"ok",…}`
- [ ] Phone: open site → `/install` → Add to Home Screen (Android + iPhone)

## 5. Security
- [ ] Run tests: `python -m pytest tests/ -v`
- [ ] Unverified users redirected to `/verify`
- [ ] OTP never stored plain text (`otp_hash` only)
- [ ] CSRF enabled in production (default)

## 6. Search / mobile
- [ ] Google Search Console: submit `/sitemap.xml`
- [ ] PWA install works over HTTPS only

## Commands
```bash
python scripts/check_providers.py
python -m pytest tests/ -v
gunicorn app:app --bind 0.0.0.0:$PORT
```
