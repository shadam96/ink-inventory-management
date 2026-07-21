"""Shared helper for generating sequential document numbers (PREFIX-YYMMDD-NNN).

Used by both receiving_service.py (batch/GRN numbers) and
document_service.py (delivery note numbers), which previously each
reimplemented the same "find today's highest suffix and increment it"
algorithm independently.
"""
from datetime import datetime
from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm.attributes import InstrumentedAttribute


async def generate_sequential_number(
    db: AsyncSession,
    column: InstrumentedAttribute,
    prefix: str,
    pad_width: int = 3,
    date_str: Optional[str] = None,
) -> str:
    """Generate ``PREFIX-YYMMDD-NNN`` by finding the highest existing
    suffix for today's date (against ``column``) and incrementing it."""
    date_str = date_str or datetime.now().strftime("%y%m%d")
    prefix_pattern = f"{prefix}-{date_str}-%"

    result = await db.execute(select(func.max(column)).where(column.like(prefix_pattern)))
    last_value = result.scalar()

    if last_value:
        try:
            next_seq = int(last_value.split("-")[-1]) + 1
        except (ValueError, IndexError):
            next_seq = 1
    else:
        next_seq = 1

    return f"{prefix}-{date_str}-{next_seq:0{pad_width}d}"
