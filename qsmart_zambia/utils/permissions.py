"""
Fine-grained RBAC for QSMART Zambia.

Roles (staff hierarchy + customer + super admin):
  super_admin       – system-wide control
  institution_admin – manage one institution
  supervisor        – oversee queues & staff at institution
  receptionist      – register/call customers, view queries
  counter_staff     – serve at counter, complete tickets
  staff             – generic approved staff (legacy/default)
  customer          – public user

Permissions are explicit; check with user_can(user, 'permission_code').
"""

# permission codes
PERMS = {
    'admin.dashboard': 'View system admin dashboard',
    'admin.staff_approve': 'Approve/reject staff applications',
    'admin.institutions': 'Manage all institutions',
    'admin.reports': 'View system reports & audit',
    'admin.users': 'Manage customers & admins',
    'admin.security': 'Security settings & retention',
    'admin.create_admin': 'Create administrator accounts',
    'inst.manage': 'Manage own institution settings',
    'inst.staff_view': 'View staff at own institution',
    'queue.view': 'View live queue',
    'queue.call': 'Call next customer',
    'queue.serve': 'Mark serving / complete',
    'queue.skip': 'Skip ticket',
    'query.view': 'View institution queries',
    'query.reply': 'Reply to customer queries',
    'query.resolve': 'Resolve/close queries',
    'display.public': 'Public ticket board (no names)',
    'customer.queue': 'Join queues',
    'customer.query': 'Submit queries',
}

ROLE_PERMS = {
    'super_admin': set(PERMS.keys()),
    'admin': {  # treated as super_admin alias for existing accounts
        'admin.dashboard', 'admin.staff_approve', 'admin.institutions',
        'admin.reports', 'admin.users', 'admin.security', 'admin.create_admin',
        'queue.view', 'queue.call', 'queue.serve', 'queue.skip',
        'query.view', 'query.reply', 'query.resolve', 'display.public',
        'inst.manage', 'inst.staff_view',
    },
    'institution_admin': {
        'inst.manage', 'inst.staff_view',
        'queue.view', 'queue.call', 'queue.serve', 'queue.skip',
        'query.view', 'query.reply', 'query.resolve', 'display.public',
    },
    'supervisor': {
        'inst.staff_view',
        'queue.view', 'queue.call', 'queue.serve', 'queue.skip',
        'query.view', 'query.reply', 'query.resolve', 'display.public',
    },
    'receptionist': {
        'queue.view', 'queue.call',
        'query.view', 'query.reply', 'display.public',
    },
    'counter_staff': {
        'queue.view', 'queue.call', 'queue.serve', 'queue.skip',
        'display.public',
    },
    'staff': {  # default approved staff
        'queue.view', 'queue.call', 'queue.serve', 'queue.skip',
        'query.view', 'query.reply', 'query.resolve', 'display.public',
    },
    'customer': {
        'customer.queue', 'customer.query',
    },
}

# Staff sub-roles that require institution + approval
STAFF_ROLES = {
    'institution_admin', 'supervisor', 'receptionist',
    'counter_staff', 'staff',
}


def effective_role(user):
    if not user or not getattr(user, 'is_authenticated', False):
        return None
    role = getattr(user, 'role', None)
    if role == 'admin':
        return 'super_admin' if getattr(user, 'is_super_admin', False) or True else 'admin'
    # Staff with staff_role field
    if role == 'staff' and getattr(user, 'staff_status', None) == 'approved':
        return getattr(user, 'staff_role', None) or 'staff'
    return role


def user_can(user, permission):
    if not user or not getattr(user, 'is_active', True):
        return False
    if getattr(user, 'role', None) == 'admin' and getattr(user, 'is_active', True):
        # system admin has all unless suspended
        return True
    er = effective_role(user)
    if not er:
        return False
    if er == 'staff' and getattr(user, 'staff_status', None) != 'approved':
        return False
    return permission in ROLE_PERMS.get(er, set())


def user_permissions(user):
    er = effective_role(user)
    if getattr(user, 'role', None) == 'admin':
        return set(PERMS.keys())
    return set(ROLE_PERMS.get(er or '', set()))
