"""Shared expiration-risk classification (days-until-expiration -> level).

fefo_engine.py, inventory_service.py, and dashboard_service.py each
independently reimplemented the same 30/60/90-day critical/warning/caution
boundaries. Centralized here so they can't drift out of sync.

Note: receiving_service.py's `validate_expiration_warning` is a distinct,
receiving-time "heads up" check (critical/warning/info tiers, with an
adjustable 180-day info window) rather than this 5-level classification,
so it isn't folded in here - but it reuses CRITICAL_THRESHOLD_DAYS /
WARNING_THRESHOLD_DAYS for its own critical/warning cutoffs.
"""

CRITICAL_THRESHOLD_DAYS = 30
WARNING_THRESHOLD_DAYS = 60
CAUTION_THRESHOLD_DAYS = 90


def classify_expiration(days_until_expiration: int) -> str:
    """Returns one of "expired", "critical", "warning", "caution", "safe"."""
    if days_until_expiration <= 0:
        return "expired"
    elif days_until_expiration <= CRITICAL_THRESHOLD_DAYS:
        return "critical"
    elif days_until_expiration <= WARNING_THRESHOLD_DAYS:
        return "warning"
    elif days_until_expiration <= CAUTION_THRESHOLD_DAYS:
        return "caution"
    return "safe"
