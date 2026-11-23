# Deploy QSMART Zambia on Render (HTTPS for phones)

Follow these steps once. You will get a permanent URL like  
`https://qsmart-zambia.onrender.com` that works on Android and iPhone.

---

## Before you start

1. A free [GitHub](https://github.com) account  
2. A free [Render](https://render.com) account (sign up with GitHub is easiest)  
3. This project folder (`qsmart_zambia`)

---

## Step 1 — Put the code on GitHub

### Option A — GitHub website

1. Open [github.com/new](https://github.com/new)  
2. Repository name: `qsmart-zambia` (public or private)  
3. **Do not** add README / .gitignore (we already have them)  
4. Create repository  
5. On your computer:

```bash
cd qsmart_zambia
git init
git add .
git commit -m "QSMART Zambia production deploy"
git branch -M main
git remote add origin https://github.com/YOUR_USERNAME/qsmart-zambia.git
git push -u origin main
```

Replace `YOUR_USERNAME` with your GitHub username.

### Option B — GitHub Desktop

Drag the `qsmart_zambia` folder into GitHub Desktop → publish repository.

---

## Step 2 — Deploy with Render Blueprint

1. Log in at [dashboard.render.com](https://dashboard.render.com)  
2. Click **New +** → **Blueprint**  
3. Connect GitHub if asked → select the **qsmart-zambia** repo  
4. Render reads `render.yaml` and shows:
   - Web service: `qsmart-zambia`  
   - Database: `qsmart-db`  
5. When prompted for **ADMIN_PASSWORD**, enter a strong password (save it)  
6. Leave other `sync: false` fields empty for now (SMS/email keys later)  
7. Click **Apply** / **Deploy**

Wait 3–8 minutes for the first build.

---

## Step 3 — Confirm it is live

1. In Render → your **qsmart-zambia** service → open the URL  
2. Check health: `https://YOUR-APP.onrender.com/health`  
   Should return: `{"status":"ok","app":"QSMART Zambia","database":"ok"}`  
3. Home page should load  
4. Login: username **admin**, password = the **ADMIN_PASSWORD** you set  

**Note:** Free services sleep after ~15 minutes idle. The first request after sleep can take 30–60 seconds.

---

## Step 4 — Install on phones

1. On your **phone**, open `https://YOUR-APP.onrender.com/install`  
2. **Android (Chrome):** menu ⋮ → Install app / Add to Home screen  
3. **iPhone (Safari):** Share → Add to Home Screen  

HTTPS is required — Render provides it automatically.

---

## Step 5 — Live SMS & email (optional but recommended)

In Render → **qsmart-zambia** → **Environment** → add/edit:

| Key | Value |
|-----|--------|
| `SMS_PROVIDER` | `africastalking` |
| `SMS_API_KEY` | your Africa's Talking key |
| `SMS_USERNAME` | `sandbox` or live username |
| `EMAIL_PROVIDER` | `resend` |
| `RESEND_API_KEY` | `re_…` |
| `MAIL_DEFAULT_SENDER` | `QSMART Zambia <you@yourdomain.com>` |

Save → service redeploys. Details: `SETUP_EMAIL_SMS.md`.

---

## Step 6 — Google search (optional)

1. [Google Search Console](https://search.google.com/search-console)  
2. Add property = your Render URL  
3. Submit sitemap: `https://YOUR-APP.onrender.com/sitemap.xml`

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| Build fails | Open **Logs** tab; usually missing dependency — `requirements.txt` is complete |
| App crashes on start | Check **ADMIN_PASSWORD** is set; check database is linked (`DATABASE_URL`) |
| `/health` shows database error | Wait for Postgres to finish provisioning; redeploy web service |
| Install app missing on phone | Must use **https://** URL, not http; open on the phone itself |
| Sleep / slow first load | Normal on free tier; upgrade plan if you need always-on |

---

## After deploy checklist

- [ ] `/health` → ok  
- [ ] Admin login works  
- [ ] Register + OTP (log mode or live SMS/email)  
- [ ] `/install` on Android and iPhone  
- [ ] SMS/email keys added when ready  

Your public base URL is the one shown on the Render service page.
