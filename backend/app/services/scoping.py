"""Plain (non-FastAPI) query-filter helpers for AccessScope-based row
scoping. Kept separate from app.api.deps because DashboardService and
other services need to apply the same filters without request-scoped
dependencies.
"""
from typing import Optional

from sqlalchemy import select
from sqlalchemy.orm import InstrumentedAttribute

from app.api.deps import AccessScope
from app.models.batch import Batch
from app.models.delivery_note import DeliveryNote, DeliveryNoteItem
from app.models.user import User


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


def batch_access_filter(user: User, scope: AccessScope):
    """WHERE-clause element for the batches this user may see or act on, or
    None if unrestricted: staff get their assigned locations (see
    get_access_scope)."""
    return batch_location_filter(scope)


def delivery_note_location_filter(scope: AccessScope):
    """WHERE-clause element restricting to delivery notes with at least one
    line from a batch at the scope's locations, or None if unrestricted."""
    if scope.location_ids is None:
        return None
    in_scope = (
        select(DeliveryNoteItem.delivery_note_id)
        .join(Batch, DeliveryNoteItem.batch_id == Batch.id)
        .where(Batch.location_id.in_(scope.location_ids))
    )
    return DeliveryNote.id.in_(in_scope)
