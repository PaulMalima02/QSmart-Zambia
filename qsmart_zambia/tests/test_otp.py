"""Secure OTP: hash storage, attempts, cooldown, verify."""


def test_generate_otp_is_six_digits():
    from utils.otp import generate_otp
    code = generate_otp()
    assert len(code) == 6
    assert code.isdigit()


def test_issue_and_verify_otp(app, db_session):
    from models.user import User
    from utils.otp import issue_otp, verify_otp, get_onscreen_otp

    with app.app_context():
        u = User(
            username='otp_test',
            email='otp@test.zm',
            phone='+260971111111',
            role='customer',
        )
        u.set_password('Test1234')
        db_session.add(u)
        db_session.commit()

        with app.test_request_context():
            ok, msg = issue_otp(u, channel='sms')
            assert ok is True
            assert u.otp_hash is not None
            assert u.otp_code is None  # never plain text in DB
            assert u.otp_attempts == 0
            code = get_onscreen_otp(u)
            assert code and len(code) == 6

            ok, msg = verify_otp(u, '000000')
            assert ok is False
            assert u.otp_attempts == 1

            ok, msg = verify_otp(u, code)
            assert ok is True
            assert u.phone_verified is True
            assert u.otp_hash is None


def test_otp_max_attempts_lockout(app, db_session):
    from models.user import User
    from utils.otp import issue_otp, verify_otp, get_onscreen_otp

    with app.app_context():
        u = User(
            username='lockout',
            email='lock@test.zm',
            phone='+260972222222',
            role='customer',
        )
        u.set_password('Test1234')
        db_session.add(u)
        db_session.commit()
        app.config['OTP_MAX_ATTEMPTS'] = 3

        with app.test_request_context():
            issue_otp(u, channel='sms')
            for _ in range(3):
                verify_otp(u, '111111')
            assert u.otp_attempts >= 3
            code = get_onscreen_otp(u)
            ok, msg = verify_otp(u, code or '999999')
            assert ok is False
            assert 'attempt' in msg.lower() or 'new code' in msg.lower()


def test_resend_cooldown(app, db_session):
    from models.user import User
    from utils.otp import issue_otp, can_resend

    with app.app_context():
        u = User(
            username='cooldown',
            email='cd@test.zm',
            phone='+260973333333',
            role='customer',
        )
        u.set_password('Test1234')
        db_session.add(u)
        db_session.commit()
        app.config['OTP_RESEND_COOLDOWN_SECONDS'] = 60

        with app.test_request_context():
            ok, _ = issue_otp(u, channel='sms')
            assert ok
            allowed, remaining = can_resend(u)
            assert allowed is False
            assert remaining > 0
            ok2, msg = issue_otp(u, channel='sms')
            assert ok2 is False
            assert 'wait' in msg.lower()
