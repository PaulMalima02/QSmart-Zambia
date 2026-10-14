#!/usr/bin/env python3
"""Check SMS / email provider configuration for QSMART Zambia.

Usage:
  python scripts/check_providers.py
  python scripts/check_providers.py --send   # optional real test send (needs keys)
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


def main():
    send = '--send' in sys.argv
    print('QSMART Zambia — provider check\n')

    sms_provider = (os.environ.get('SMS_PROVIDER') or 'log').lower()
    sms_key = os.environ.get('SMS_API_KEY') or ''
    sms_user = os.environ.get('SMS_USERNAME') or 'sandbox'
    print('SMS')
    print(f'  SMS_PROVIDER = {sms_provider}')
    print(f'  SMS_USERNAME = {sms_user}')
    print(f'  SMS_API_KEY  = {"set (" + str(len(sms_key)) + " chars)" if sms_key else "NOT SET"}')
    if sms_provider in ('log', '', 'none') or not sms_key:
        print('  Status       = LOCAL LOG only (codes in terminal + verify page)')
    elif sms_provider == 'africastalking':
        print('  Status       = Africa\'s Talking configured')
    elif sms_provider == 'twilio':
        print('  Status       = Twilio configured' if ':' in sms_key else '  Status = Twilio key should be SID:TOKEN')
    else:
        print(f'  Status       = Unknown provider "{sms_provider}"')

    email_provider = (os.environ.get('EMAIL_PROVIDER') or '').lower()
    resend_key = os.environ.get('RESEND_API_KEY') or ''
    mail_server = os.environ.get('MAIL_SERVER') or ''
    sender = os.environ.get('MAIL_DEFAULT_SENDER') or 'noreply@qsmart.zm'
    print('\nEmail')
    print(f'  EMAIL_PROVIDER     = {email_provider or "(empty → SMTP if MAIL_SERVER set)"}')
    print(f'  RESEND_API_KEY     = {"set (" + str(len(resend_key)) + " chars)" if resend_key else "NOT SET"}')
    print(f'  MAIL_SERVER        = {mail_server or "NOT SET"}')
    print(f'  MAIL_DEFAULT_SENDER= {sender}')
    if email_provider == 'resend' and resend_key:
        print('  Status             = Resend configured')
    elif mail_server:
        print('  Status             = SMTP configured')
    else:
        print('  Status             = LOCAL LOG only (no delivery)')

    print('\nOTP settings')
    for k, d in [
        ('OTP_EXPIRY_MINUTES', '5'),
        ('OTP_MAX_ATTEMPTS', '5'),
        ('OTP_RESEND_COOLDOWN_SECONDS', '60'),
    ]:
        print(f'  {k} = {os.environ.get(k, d)}')

    if not send:
        print('\nTip: run with --send to attempt a test message (requires Flask app context + keys).')
        print('See SETUP_EMAIL_SMS.md for full instructions.')
        return

    # Optional live test
    from app import create_app
    app = create_app()
    with app.app_context():
        to_phone = os.environ.get('TEST_PHONE', '')
        to_email = os.environ.get('TEST_EMAIL', '')
        if to_phone:
            from utils.sms import send_sms
            ok, st = send_sms(to_phone, 'QSMART test SMS — configuration OK.', message_type='test')
            print(f'\nTest SMS to {to_phone}: ok={ok} status={st}')
        else:
            print('\nSet TEST_PHONE=+260… in .env to send a test SMS.')
        if to_email:
            from utils.email_util import send_email
            ok, st = send_email(to_email, 'QSMART test email', 'Configuration OK.')
            print(f'Test email to {to_email}: ok={ok} status={st}')
        else:
            print('Set TEST_EMAIL=you@example.com in .env to send a test email.')


if __name__ == '__main__':
    main()
