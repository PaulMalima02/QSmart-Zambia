"""Zambia-focused smart wait-time prediction and counter recommendation."""
from datetime import datetime, timedelta


def estimate_wait_minutes(service, position=None):
    """
    Smart wait estimate using:
    - people ahead
    - open counters for this service/institution
    - rolling average of recent completed service times
    - time-of-day factor (busier mid-morning / lunch in Zambian service centres)
    """
    from models.queue import QueueTicket
    from models.service import Counter

    if position is None:
        position = QueueTicket.query.filter_by(
            service_id=service.id, status='waiting'
        ).count() + 1

    people_ahead = max(int(position) - 1, 0)
    open_counters = _open_counters_for_service(service)
    avg = _adaptive_avg_minutes(service) or (service.avg_service_time or 10)
    factor = _tod_factor()

    # Parallelism: divide by open counters
    estimate = (people_ahead * avg * factor) / max(open_counters, 1)
    return max(int(round(estimate)), 0)


def recommend_counter(service, institution_id=None):
    """
    Recommend the least-busy open counter for a service/institution.
    Returns (counter, reason_str) or (None, reason).
    """
    from models.service import Counter
    from models.queue import QueueTicket

    inst_id = institution_id or service.institution_id
    counters = Counter.query.filter_by(
        institution_id=inst_id, is_open=True
    ).all()
    # Prefer counters linked to this service, else any open at institution
    preferred = [c for c in counters if c.service_id == service.id]
    pool = preferred or counters
    if not pool:
        return None, 'No open counters right now'

    best = None
    best_load = 10**9
    for c in pool:
        # serving/called on this counter
        load = QueueTicket.query.filter(
            QueueTicket.counter_id == c.id,
            QueueTicket.status.in_(['called', 'serving'])
        ).count()
        # slight preference if dedicated to this service
        if c.service_id == service.id:
            load -= 0.1
        if load < best_load:
            best_load = load
            best = c

    if best is None:
        return None, 'No counter available'
    reason = f'Recommended: {best.name} (least busy right now)'
    return best, reason


def _open_counters_for_service(service):
    from models.service import Counter
    n = Counter.query.filter_by(
        institution_id=service.institution_id, is_open=True
    ).count()
    return n or 1


def _adaptive_avg_minutes(service):
    """Average duration of last completed tickets for this service (up to 50)."""
    from models.queue import QueueTicket
    since = datetime.utcnow() - timedelta(days=14)
    rows = (
        QueueTicket.query.filter(
            QueueTicket.service_id == service.id,
            QueueTicket.status == 'completed',
            QueueTicket.completed_at.isnot(None),
            QueueTicket.started_at.isnot(None),
            QueueTicket.completed_at >= since,
        )
        .order_by(QueueTicket.completed_at.desc())
        .limit(50)
        .all()
    )
    durations = []
    for t in rows:
        try:
            mins = (t.completed_at - (t.started_at or t.called_at or t.joined_at)).total_seconds() / 60.0
            if 0.5 < mins < 180:
                durations.append(mins)
        except Exception:
            continue
    if not durations:
        return None
    return sum(durations) / len(durations)


def _tod_factor():
    """Busier periods at typical Zambian public offices (approx.)."""
    hour = datetime.utcnow().hour + 2  # CAT ≈ UTC+2
    if hour < 0:
        hour += 24
    hour = hour % 24
    if 8 <= hour <= 10:
        return 1.25   # morning rush
    if 12 <= hour <= 14:
        return 1.15   # lunch peak
    if 15 <= hour <= 16:
        return 1.1
    if hour >= 17 or hour < 7:
        return 0.85
    return 1.0


def pickup_prediction(ticket):
    """
    Human-readable prediction for when the customer should head to the premises.
    """
    wait = ticket.estimated_wait
    if wait is None:
        wait = estimate_wait_minutes(ticket.service, ticket.position)
    if wait <= 5:
        return 'Head to the counter now — you will be called very soon.'
    if wait <= 15:
        return f'Leave for the premises in about {max(wait - 5, 0)} minutes so you arrive on time.'
    return f'Estimated wait ~{wait} min. We will SMS you when only 2 people are ahead.'
