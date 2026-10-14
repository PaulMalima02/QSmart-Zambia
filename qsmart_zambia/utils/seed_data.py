"""Idempotent seed: institutions, branches, services, demo customer. Admin via env only."""
from utils.database import db
from models.user import User
from models.institution import Institution, InstitutionBranch
from models.service import Service, Counter


# Real Zambian institutions (Lusaka-focused). Coordinates approximate; coords_verified=False unless known.
INSTITUTIONS = [
    {
        'name': 'Patents and Companies Registration Agency (PACRA)',
        'code': 'PACRA', 'category': 'government',
        'phone': '+260 211 255151',
        'branches': [{'name': 'Lusaka Head Office', 'address': 'Plot 8472, Nasser Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4085, 'longitude': 28.3065}],
        'services': [('Company Registration', 25), ('Business Name Search', 10), ('Annual Returns', 15)],
    },
    {
        'name': 'Drug Enforcement Commission (DEC)',
        'code': 'DEC', 'category': 'government', 'phone': '+260 211 254391',
        'branches': [{'name': 'Lusaka Office', 'address': 'Fairley Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4120, 'longitude': 28.2900}],
        'services': [('Public Complaints', 15), ('General Enquiry', 10)],
    },
    {
        'name': 'Zambia Revenue Authority (ZRA)',
        'code': 'ZRA', 'category': 'government', 'phone': '+260 211 381111',
        'branches': [{'name': 'Revenue House', 'address': 'Cairo Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4195, 'longitude': 28.2835}],
        'services': [('TPIN Registration', 10), ('Tax Returns', 15), ('Customs Clearance', 25)],
    },
    {
        'name': 'Road Transport and Safety Agency (RTSA)',
        'code': 'RTSA', 'category': 'government', 'phone': '+260 211 255544',
        'branches': [{'name': 'Lusaka', 'address': 'Dedan Kimathi Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4200, 'longitude': 28.2950}],
        'services': [('Driving Licence', 20), ('Vehicle Registration', 15), ('Road Tax', 8)],
    },
    {
        'name': 'National Pension Scheme Authority (NAPSA)',
        'code': 'NAPSA', 'category': 'government', 'phone': '+260 211 260333',
        'branches': [{'name': 'Lusaka', 'address': 'Lubwa Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4000, 'longitude': 28.3200}],
        'services': [('Member Registration', 15), ('Benefit Claims', 20)],
    },
    {
        'name': 'National Health Insurance Management Authority (NHIMA)',
        'code': 'NHIMA', 'category': 'government', 'phone': '+260 211 255000',
        'branches': [{'name': 'Lusaka', 'address': 'Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4100, 'longitude': 28.3000}],
        'services': [('Member Registration', 15), ('Claims Enquiry', 12)],
    },
    {
        'name': 'Workers Compensation Fund Control Board',
        'code': 'WCFCB', 'category': 'government', 'phone': '+260 211 227830',
        'branches': [{'name': 'Compensation House', 'address': 'Cairo Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4175, 'longitude': 28.2840}],
        'services': [('Claim Lodging', 20), ('Employer Registration', 15)],
    },
    {
        'name': 'Lusaka City Council',
        'code': 'LCC', 'category': 'government', 'phone': '+260 211 251544',
        'branches': [{'name': 'Civic Centre', 'address': 'Independence Avenue, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4220, 'longitude': 28.3050}],
        'services': [('Business Levy', 12), ('Rates Payment', 10), ('Planning Permission', 25)],
    },
    {
        'name': 'Department of National Registration, Passport and Citizenship',
        'code': 'PASSPORT', 'category': 'government', 'phone': '+260 211 254477',
        'branches': [{'name': 'Lusaka', 'address': 'Independence Avenue, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4250, 'longitude': 28.3100}],
        'services': [('Passport Application', 30), ('Passport Collection', 10), ('NRC Services', 15)],
    },
    {
        'name': 'Immigration Department',
        'code': 'IMMIG', 'category': 'government',
        'branches': [{'name': 'Lusaka', 'address': 'Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4180, 'longitude': 28.2980}],
        'services': [('Visa Services', 25), ('Permit Applications', 30)],
    },
    {
        'name': 'Zambia National Commercial Bank (Zanaco)',
        'code': 'ZANACO', 'category': 'bank', 'phone': '+260 211 228858',
        'branches': [{'name': 'Cairo Road', 'address': 'Cairo Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4167, 'longitude': 28.2833}],
        'services': [('Account Opening', 15), ('Cash Services', 5), ('Loans', 20)],
    },
    {
        'name': 'Absa Bank Zambia',
        'code': 'ABSA', 'category': 'bank', 'phone': '+260 211 366100',
        'branches': [{'name': 'Cairo Road', 'address': 'Cairo Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4180, 'longitude': 28.2820}],
        'services': [('Teller Services', 6), ('Account Services', 12)],
    },
    {
        'name': 'Stanbic Bank Zambia',
        'code': 'STANBIC', 'category': 'bank',
        'branches': [{'name': 'Lusaka Main', 'address': 'Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4150, 'longitude': 28.2850}],
        'services': [('Personal Banking', 10), ('Business Banking', 15)],
    },
    {
        'name': 'First National Bank Zambia',
        'code': 'FNB', 'category': 'bank',
        'branches': [{'name': 'Lusaka', 'address': 'Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4140, 'longitude': 28.2880}],
        'services': [('Account Services', 10), ('Card Services', 8)],
    },
    {
        'name': 'University Teaching Hospital (UTH)',
        'code': 'UTH', 'category': 'hospital', 'phone': '+260 211 251400',
        'branches': [{'name': 'Main Campus', 'address': 'Nationalist Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.4320, 'longitude': 28.3120}],
        'services': [('OPD Registration', 8), ('Pharmacy', 5), ('Laboratory Results', 7)],
    },
    {
        'name': 'Levy Mwanawasa University Teaching Hospital',
        'code': 'LMUTH', 'category': 'hospital',
        'branches': [{'name': 'Main', 'address': 'Great East Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.3950, 'longitude': 28.3400}],
        'services': [('OPD Registration', 8), ('Pharmacy', 5)],
    },
    {
        'name': 'ZESCO Limited',
        'code': 'ZESCO', 'category': 'utility', 'phone': '+260 211 361111',
        'branches': [{'name': 'Lusaka Customer Service', 'address': 'Great East Road, Lusaka', 'city': 'Lusaka',
                      'latitude': -15.3900, 'longitude': 28.3500}],
        'services': [('New Connection', 20), ('Billing Enquiries', 8), ('Fault Reporting', 5)],
    },
]


def seed_all(app):
    with app.app_context():
        try:
            _seed_institutions()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print('seed institutions:', e)

        try:
            _seed_demo_customer()
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print('seed demo:', e)

        try:
            _seed_admin_from_env(app)
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print('seed admin:', e)

        print('✓ QSMART Zambia seed complete')


def _seed_institutions():
    for data in INSTITUTIONS:
        inst = Institution.query.filter_by(code=data['code']).first()
        if not inst:
            inst = Institution(
                name=data['name'], code=data['code'], category=data['category'],
                phone=data.get('phone'), is_active=True,
            )
            db.session.add(inst)
            db.session.flush()

        for b in data.get('branches', []):
            existing = InstitutionBranch.query.filter_by(
                institution_id=inst.id, name=b['name']
            ).first()
            if not existing:
                branch = InstitutionBranch(
                    institution_id=inst.id,
                    name=b['name'],
                    address=b.get('address'),
                    city=b.get('city', 'Lusaka'),
                    latitude=b.get('latitude'),
                    longitude=b.get('longitude'),
                    coords_verified=False,
                    is_active=True,
                )
                db.session.add(branch)
                db.session.flush()
            else:
                branch = existing

            for svc_name, avg in data.get('services', []):
                if not Service.query.filter_by(institution_id=inst.id, name=svc_name).first():
                    svc = Service(
                        institution_id=inst.id,
                        branch_id=branch.id,
                        name=svc_name,
                        avg_service_time=avg,
                        is_active=True,
                    )
                    db.session.add(svc)
                    db.session.flush()
                    db.session.add(Counter(
                        institution_id=inst.id, service_id=svc.id,
                        name=f'Counter 1', is_open=True,
                    ))


def _seed_demo_customer():
    if User.query.filter(
        (User.username == 'demo') | (User.email == 'demo@qsmart.zm')
    ).first():
        return
    u = User(
        username='demo', email='demo@qsmart.zm', full_name='Demo Customer',
        phone='+260977000000', role='customer', is_active=True,
        email_verified=True, phone_verified=True,
    )
    u.set_password('Demo123!')
    db.session.add(u)


def _seed_admin_from_env(app):
    """Create first admin from environment only — never public registration."""
    import os
    username = os.environ.get('ADMIN_USERNAME', 'admin')
    password = os.environ.get('ADMIN_PASSWORD', 'Admin123!')
    email = os.environ.get('ADMIN_EMAIL', 'admin@qsmart.zm')

    # Already exists by username or email — do not insert again
    existing = User.query.filter(
        (User.username == username) | (User.email == email)
    ).first()
    if existing:
        if existing.role != 'admin':
            existing.role = 'admin'
            existing.staff_status = 'approved'
            existing.is_active = True
            print(f'✓ Existing user elevated to admin: {username}')
        else:
            print(f'✓ Admin already present: {username}')
        return

    max_admins = app.config.get('MAX_ADMIN_ACCOUNTS', 2)
    if User.query.filter_by(role='admin').count() >= max_admins:
        print('✓ Admin limit reached; skip creating admin')
        return

    u = User(
        username=username, email=email, full_name='System Administrator',
        role='admin', staff_status='approved', is_active=True,
        email_verified=True, phone_verified=True,
    )
    u.set_password(password)
    db.session.add(u)
    print(f'✓ Initial admin created: {username}')
