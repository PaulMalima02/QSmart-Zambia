from flask import Blueprint, render_template, redirect, url_for, Response, request, flash, current_app

main_bp = Blueprint('main', __name__)


@main_bp.route('/')
def index():
    from flask_login import current_user
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for('admin.dashboard'))
        if current_user.is_staff:
            return redirect(url_for('staff.dashboard'))
        if current_user.is_pending_staff:
            return redirect(url_for('auth.pending'))
        return redirect(url_for('customer.dashboard'))
    return render_template('index.html', show_auth_modal=True)


@main_bp.route('/privacy')
def privacy():
    return render_template('privacy.html')


@main_bp.route('/install')
def install():
    """Platform-specific install guide for Android and iPhone."""
    return render_template('install.html')



@main_bp.route('/health')
def health():
    """Liveness/readiness for Render, Railway, load balancers."""
    from flask import jsonify
    from utils.database import db
    status = {'status': 'ok', 'app': 'QSMART Zambia'}
    code = 200
    try:
        from sqlalchemy import text
        db.session.execute(text('SELECT 1'))
        status['database'] = 'ok'
    except Exception as e:
        status['database'] = 'error'
        status['status'] = 'degraded'
        status['detail'] = str(e)[:120]
        code = 503
    return jsonify(status), code


@main_bp.route('/display/<int:institution_id>')
def public_board(institution_id):
    """Unauthenticated public board — ticket numbers only."""
    from models.service import Service
    from models.queue import QueueTicket
    from models.institution import Institution
    inst = Institution.query.get_or_404(institution_id)
    svc_ids = [s.id for s in Service.query.filter_by(institution_id=inst.id).all()]
    waiting = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status == 'waiting'
    ).order_by(QueueTicket.joined_at.asc()).limit(20).all() if svc_ids else []
    serving = QueueTicket.query.filter(
        QueueTicket.service_id.in_(svc_ids), QueueTicket.status.in_(['called', 'serving'])
    ).all() if svc_ids else []
    return render_template('staff/public_display.html', waiting=waiting, serving=serving, institution=inst)


@main_bp.route('/robots.txt')
def robots_txt():
    """Allow search engines to index public pages."""
    base = request.url_root.rstrip('/')
    body = f"""User-agent: *
Allow: /
Allow: /privacy
Allow: /login
Allow: /register
Allow: /install
Disallow: /admin
Disallow: /staff
Disallow: /customer
Disallow: /verify
Disallow: /reset-password

Sitemap: {base}/sitemap.xml
"""
    return Response(body, mimetype='text/plain')


@main_bp.route('/sitemap.xml')
def sitemap_xml():
    """Basic sitemap for search engines."""
    base = request.url_root.rstrip('/')
    urls = [
        ('/', '1.0', 'daily'),
        ('/privacy', '0.5', 'monthly'),
        ('/login', '0.8', 'weekly'),
        ('/register', '0.8', 'weekly'),
    ]
    items = []
    for path, pri, freq in urls:
        items.append(
            f'  <url>\n'
            f'    <loc>{base}{path}</loc>\n'
            f'    <changefreq>{freq}</changefreq>\n'
            f'    <priority>{pri}</priority>\n'
            f'  </url>'
        )
    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
        + '\n'.join(items)
        + '\n</urlset>\n'
    )
    return Response(xml, mimetype='application/xml')


@main_bp.route('/setup-email', methods=['GET', 'POST'])
def setup_email():
    """One-page wizard: paste Resend API key or SMTP settings so OTP emails work."""
    from pathlib import Path
    import os
    env_path = Path(current_app.root_path) / '.env'
    status = {'configured': False, 'provider': '', 'message': ''}

    def _read_env():
        data = {}
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                line = line.strip()
                if not line or line.startswith('#') or '=' not in line:
                    continue
                k, _, v = line.partition('=')
                data[k.strip()] = v.strip().strip('"').strip("'")
        return data

    def _write_env_keys(updates):
        existing = {}
        lines_out = []
        if env_path.exists():
            for line in env_path.read_text(encoding='utf-8', errors='ignore').splitlines():
                if '=' in line and not line.strip().startswith('#'):
                    k = line.split('=', 1)[0].strip()
                    existing[k] = line
                else:
                    lines_out.append(line)
        else:
            lines_out = []
        for k, v in updates.items():
            existing[k] = f'{k}={v}'
        # rebuild: keep comments from template-ish order
        order = [
            'SECRET_KEY', 'ADMIN_USERNAME', 'ADMIN_PASSWORD', 'ADMIN_EMAIL',
            'EMAIL_PROVIDER', 'RESEND_API_KEY', 'MAIL_DEFAULT_SENDER',
            'MAIL_SERVER', 'MAIL_PORT', 'MAIL_USERNAME', 'MAIL_PASSWORD', 'MAIL_USE_TLS',
            'SMS_PROVIDER', 'OTP_EXPIRY_MINUTES', 'OTP_MAX_ATTEMPTS', 'OTP_RESEND_COOLDOWN_SECONDS',
            'FLASK_ENV',
        ]
        final = []
        seen = set()
        for k in order:
            if k in existing:
                final.append(existing[k])
                seen.add(k)
        for k, line in existing.items():
            if k not in seen:
                final.append(line)
        env_path.write_text('\n'.join(final) + '\n', encoding='utf-8')
        # live-update config for current process
        for k, v in updates.items():
            os.environ[k] = v
            if k in current_app.config:
                current_app.config[k] = v
            # map env names to config
        if 'EMAIL_PROVIDER' in updates:
            current_app.config['EMAIL_PROVIDER'] = updates['EMAIL_PROVIDER']
        if 'RESEND_API_KEY' in updates:
            current_app.config['RESEND_API_KEY'] = updates['RESEND_API_KEY']
        if 'MAIL_DEFAULT_SENDER' in updates:
            current_app.config['MAIL_DEFAULT_SENDER'] = updates['MAIL_DEFAULT_SENDER']
        if 'MAIL_SERVER' in updates:
            current_app.config['MAIL_SERVER'] = updates['MAIL_SERVER']
        if 'MAIL_PORT' in updates:
            current_app.config['MAIL_PORT'] = int(updates['MAIL_PORT'] or 587)
        if 'MAIL_USERNAME' in updates:
            current_app.config['MAIL_USERNAME'] = updates['MAIL_USERNAME']
        if 'MAIL_PASSWORD' in updates:
            current_app.config['MAIL_PASSWORD'] = updates['MAIL_PASSWORD']
        if 'MAIL_USE_TLS' in updates:
            current_app.config['MAIL_USE_TLS'] = updates['MAIL_USE_TLS'].lower() in ('1', 'true', 'yes')

    env = _read_env()
    if (env.get('RESEND_API_KEY') or env.get('MAIL_SERVER')):
        status['configured'] = True
        status['provider'] = env.get('EMAIL_PROVIDER') or ('smtp' if env.get('MAIL_SERVER') else '')

    test_result = None
    if request.method == 'POST':
        action = request.form.get('action', 'save')
        if action == 'save_resend':
            key = (request.form.get('resend_api_key') or '').strip()
            sender = (request.form.get('mail_sender') or 'QSMART Zambia <onboarding@resend.dev>').strip()
            if not key.startswith('re_'):
                flash('Resend API key should start with re_', 'error')
            else:
                _write_env_keys({
                    'EMAIL_PROVIDER': 'resend',
                    'RESEND_API_KEY': key,
                    'MAIL_DEFAULT_SENDER': sender,
                    'MAIL_SERVER': '',
                })
                flash('Resend key saved to .env. Testing send next…', 'success')
                status['configured'] = True
                status['provider'] = 'resend'
        elif action == 'save_smtp':
            server = (request.form.get('mail_server') or '').strip()
            port = (request.form.get('mail_port') or '587').strip()
            user = (request.form.get('mail_username') or '').strip()
            password = (request.form.get('mail_password') or '').strip()
            sender = (request.form.get('mail_sender') or user).strip()
            if not server or not user or not password:
                flash('SMTP server, username and password are required.', 'error')
            else:
                _write_env_keys({
                    'EMAIL_PROVIDER': 'smtp',
                    'RESEND_API_KEY': '',
                    'MAIL_SERVER': server,
                    'MAIL_PORT': port,
                    'MAIL_USERNAME': user,
                    'MAIL_PASSWORD': password,
                    'MAIL_DEFAULT_SENDER': sender,
                    'MAIL_USE_TLS': 'true',
                })
                flash('SMTP settings saved to .env.', 'success')
                status['configured'] = True
                status['provider'] = 'smtp'
        elif action == 'test_send':
            to = (request.form.get('test_to') or '').strip()
            if not to:
                flash('Enter a recipient email for the test.', 'error')
            else:
                from utils.email_util import send_email
                ok, st = send_email(
                    to,
                    'QSMART Zambia — test verification email',
                    'If you see this, email is working. Sample code: 123456',
                    html_body='<p>Email is <strong>working</strong>.</p><p style="font-size:24px;letter-spacing:0.15em">123456</p>',
                )
                test_result = {'ok': ok, 'status': st, 'to': to}
                if ok:
                    flash(f'Test email sent to {to}. Check inbox and spam.', 'success')
                else:
                    flash(f'Send failed: {st}. Check SMTP password / Resend key and recipient rules.', 'error')

        env = _read_env()

    return render_template(
        'setup_email.html',
        status=status,
        env=env,
        test_result=test_result,
    )

