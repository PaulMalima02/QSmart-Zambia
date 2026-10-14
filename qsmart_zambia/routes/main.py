from flask import Blueprint, render_template, redirect, url_for, Response, request

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
