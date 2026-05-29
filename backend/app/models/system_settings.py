"""System-wide settings (singleton row).

Holds preferences shared across all users — currently the FX rates used to
convert per-item cost prices into a single display currency on the dashboard.
Rates are anchored to ILS: ``usd_to_ils`` is the price of 1 USD in ILS, and
``eur_to_ils`` is the price of 1 EUR in ILS. ILS is implicitly 1.0.
"""
from datetime import datetime
from decimal import Decimal

from sqlalchemy import DateTime, Integer, Numeric, func
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class SystemSettings(Base):
    """Singleton table — there is exactly one row, with id=1."""

    __tablename__ = "system_settings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, default=1)

    usd_to_ils: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        server_default="3.7",
    )
    eur_to_ils: Mapped[Decimal] = mapped_column(
        Numeric(12, 4),
        nullable=False,
        server_default="4.0",
    )

    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False,
    )
