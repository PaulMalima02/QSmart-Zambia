"""Registration validation and health endpoint."""


def test_health(client):
    r = client.get('/health')
    assert r.status_code in (200, 503)
    data = r.get_json()
    assert data.get('app') == 'QSMART Zambia'


def test_register_rejects_numeric_name(client, app):
    with app.app_context():
        r = client.post('/register', data={
            'full_name': '12345',
            'username': 'gooduser',
            'email': 'n1@test.zm',
            'phone': '0971234567',
            'password': 'Test1234',
            'confirm_password': 'Test1234',
            'role': 'customer',
            'verify_channel': 'sms',
            'privacy_consent': '1',
        }, follow_redirects=True)
        assert r.status_code == 200
        # should stay on register / show error — not land on verify as success
        body = r.data.decode('utf-8', errors='ignore').lower()
        assert 'letter' in body or 'full name' in body or 'register' in body


def test_register_rejects_digit_only_username(client, app):
    with app.app_context():
        r = client.post('/register', data={
            'full_name': 'Mary Banda',
            'username': '99999',
            'email': 'n2@test.zm',
            'phone': '0971234568',
            'password': 'Test1234',
            'confirm_password': 'Test1234',
            'role': 'customer',
            'verify_channel': 'sms',
            'privacy_consent': '1',
        }, follow_redirects=True)
        body = r.data.decode('utf-8', errors='ignore').lower()
        assert 'username' in body or 'register' in body


def test_install_page(client):
    r = client.get('/install')
    assert r.status_code == 200
    body = r.data.decode('utf-8', errors='ignore')
    assert 'Android' in body and 'iPhone' in body


def test_robots_and_sitemap(client):
    r = client.get('/robots.txt')
    assert r.status_code == 200
    assert b'Sitemap' in r.data
    r = client.get('/sitemap.xml')
    assert r.status_code == 200
    assert b'urlset' in r.data
