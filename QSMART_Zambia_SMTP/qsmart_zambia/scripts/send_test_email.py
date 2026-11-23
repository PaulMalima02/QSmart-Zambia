#!/usr/bin/env python3
"""Send a test verification-style email. Run from project root:

  python scripts/send_test_email.py you@example.com
"""
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.chdir(ROOT)

try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / '.env')
except ImportError:
    pass

to = (sys.argv[1] if len(sys.argv) > 1 else '').strip()
if not to:
    print('Usage: python scripts/send_test_email.py you@example.com')
    sys.exit(1)

print('EMAIL_PROVIDER =', os.environ.get('EMAIL_PROVIDER') or '(empty)')
print('RESEND_API_KEY =', 'set' if os.environ.get('RESEND_API_KEY') else 'NOT SET')
print('MAIL_SERVER    =', os.environ.get('MAIL_SERVER') or 'NOT SET')
print('Sending test to', to, '...')

from app import create_app
from utils.email_util import send_email

app = create_app()
with app.app_context():
    ok, status = send_email(
        to,
        'QSMART Zambia test — verification email',
        'If you received this, email is configured correctly.\nYour test code would look like: 123456',
        html_body='<p>If you received this, <strong>email is configured correctly</strong>.</p>'
                  '<p style="font-size:24px;letter-spacing:0.2em">123456</p>',
    )
    print('Result: ok =', ok, '| status =', status)
    if not ok:
        print()
        print('Email did NOT send. Fix:')
        print('  1. Copy .env.example to .env')
        print('  2. Set EMAIL_PROVIDER=resend and RESEND_API_KEY=re_...')
        print('  3. On Resend free tier, "to" must be YOUR Resend signup email')
        print('  4. Restart and run this script again')
        sys.exit(2)
    print('Check inbox (and spam) for:', to)
