"""Plain (non-FastAPI) query-filter helpers for AccessScope-based row
scoping. Kept separate from app.api.deps because DashboardService and
other services need to apply the same filters without request-scoped
dependencies.
"""
from typing import Optional

from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import AccessScope
from app.models.batch import Batch


def batch_location_filter(scope: AccessScope):
    """WHERE-clause element restricting to Batch.location_id, or None if
    the scope is unrestricted. Caller applies it with `.where(clause)`
    only when it isn't None."""
    if scope.location_ids is None:
        return None
    return Batch.location_id.in_(scope.location_ids)


def location_id_filter(scope: AccessScope, location_id_column: InstrumentedAttribute):
    """Same as batch_location_filter but for a caller-supplied
    location_id column (e.g. Location.id itself)."""
    if scope.location_ids is None:
        return None
    return location_id_column.in_(scope.location_ids)
