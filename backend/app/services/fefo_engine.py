"""FEFO (First Expired, First Out) Engine for inventory picking"""
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch, BatchStatus
from app.models.item import Item


@dataclass
class BatchSuggestion:
    """A suggested batch for picking"""
    batch_id: UUID
    batch_number: str
    quantity_available: Decimal
    expiration_date: date
    days_until_expiration: int
    location_code: Optional[str]
    suggested_quantity: Decimal
    warning_level: str  # "safe", "warning", "critical"
    
    def to_dict(self) -> dict:
        return {
            "batch_id": str(self.batch_id),
            "batch_number": self.batch_number,
            "quantity_available": float(self.quantity_available),
            "expiration_date": self.expiration_date.isoformat(),
            "days_until_expiration": self.days_until_expiration,
            "location_code": self.location_code,
            "suggested_quantity": float(self.suggested_quantity),
            "warning_level": self.warning_level,
        }


@dataclass
class PickingValidation:
    """Result of picking validation"""
    is_valid: bool
    batch_id: UUID
    quantity: Decimal
    errors: List[str]
    warnings: List[str]
    
    def to_dict(self) -> dict:
        return {
            "is_valid": self.is_valid,
            "batch_id": str(self.batch_id),
            "quantity": float(self.quantity),
            "errors": self.errors,
            "warnings": self.warnings,
        }


class FEFOEngine:
    """
    First Expired, First Out engine for inventory management.
    
    Suggests batches for picking based on expiration dates,
    prioritizing those expiring soonest.
    """
    
    # Warning thresholds (days)
    CRITICAL_THRESHOLD = 30
    WARNING_THRESHOLD = 60
    CAUTION_THRESHOLD = 90
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    def _get_warning_level(self, days_until_expiration: int) -> str:
        """Determine warning level based on days until expiration"""
        if days_until_expiration <= 0:
            return "expired"
        elif days_until_expiration <= self.CRITICAL_THRESHOLD:
            return "critical"
        elif days_until_expiration <= self.WARNING_THRESHOLD:
            return "warning"
        elif days_until_expiration <= self.CAUTION_THRESHOLD:
            return "caution"
        return "safe"
    
    async def get_available_batches(
        self,
        item_id: UUID,
        exclude_expired: bool = True,
    ) -> List[Batch]:
        """
        Get all available batches for an item, sorted by FEFO.
        """
        query = (
            select(Batch)
            .options(selectinload(Batch.location))
            .where(
                Batch.item_id == item_id,
                Batch.status == BatchStatus.ACTIVE,
                Batch.quantity_available > 0,
            )
            .order_by(Batch.expiration_date.asc())
        )
        
        if exclude_expired:
            query = query.where(Batch.expiration_date >= date.today())
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def suggest_batches_for_picking(
        self,
        item_id: UUID,
        quantity_needed: Decimal,
        exclude_expired: bool = True,
    ) -> List[BatchSuggestion]:
        """
        Suggest batches to pick from using FEFO logic.
        
        Returns a list of BatchSuggestion objects that together
        fulfill the requested quantity.
        """
        batches = await self.get_available_batches(item_id, exclude_expired)
        
        if not batches:
            return []
        
        suggestions = []
        remaining_quantity = quantity_needed
        today = date.today()
        
        for batch in batches:
            if remaining_quantity <= 0:
                break
            
            days_until = (batch.expiration_date - today).days
            warning_level = self._get_warning_level(days_until)
            
            # Calculate how much to take from this batch
            pick_quantity = min(batch.quantity_available, remaining_quantity)
            remaining_quantity -= pick_quantity
            
            suggestion = BatchSuggestion(
                batch_id=batch.id,
                batch_number=batch.batch_number,
                quantity_available=batch.quantity_available,
                expiration_date=batch.expiration_date,
                days_until_expiration=days_until,
                location_code=batch.location.location_code if batch.location else None,
                suggested_quantity=pick_quantity,
                warning_level=warning_level,
            )
            suggestions.append(suggestion)
        
        return suggestions
    
    async def get_total_available(self, item_id: UUID) -> Decimal:
        """Get total available quantity for an item"""
        batches = await self.get_available_batches(item_id)
        return sum(b.quantity_available for b in batches)
    
    async def can_fulfill(self, item_id: UUID, quantity_needed: Decimal) -> bool:
        """Check if requested quantity can be fulfilled"""
        total = await self.get_total_available(item_id)
        return total >= quantity_needed
    
    async def validate_picking(
        self,
        batch_id: UUID,
        quantity: Decimal,
    ) -> PickingValidation:
        """
        Validate a picking operation.
        
        Checks:
        - Batch exists and is active
        - Batch is not expired
        - Sufficient quantity available
        - No earlier expiring batches are skipped
        """
        errors = []
        warnings = []
        
        # Get the batch
        result = await self.db.execute(
            select(Batch)
            .options(selectinload(Batch.item))
            .where(Batch.id == batch_id)
        )
        batch = result.scalar_one_or_none()
        
        if not batch:
            errors.append("אצווה לא נמצאה")  # Batch not found
            return PickingValidation(
                is_valid=False,
                batch_id=batch_id,
                quantity=quantity,
                errors=errors,
                warnings=warnings,
            )
        
        today = date.today()
        days_until = (batch.expiration_date - today).days
        
        # Check if expired
        if batch.expiration_date < today:
            errors.append(f"אצווה {batch.batch_number} פגת תוקף")
            return PickingValidation(
                is_valid=False,
                batch_id=batch_id,
                quantity=quantity,
                errors=errors,
                warnings=warnings,
            )
        
        # Check if batch is active
        if batch.status != BatchStatus.ACTIVE:
            errors.append(f"אצווה {batch.batch_number} אינה פעילה (סטטוס: {batch.status.value})")
            return PickingValidation(
                is_valid=False,
                batch_id=batch_id,
                quantity=quantity,
                errors=errors,
                warnings=warnings,
            )
        
        # Check quantity
        if quantity > batch.quantity_available:
            errors.append(
                f"כמות לא מספיקה באצווה {batch.batch_number}. "
                f"זמין: {batch.quantity_available}, נדרש: {quantity}"
            )
            return PickingValidation(
                is_valid=False,
                batch_id=batch_id,
                quantity=quantity,
                errors=errors,
                warnings=warnings,
            )
        
        # Check for FEFO violations - are there earlier expiring batches?
        earlier_batches = await self.db.execute(
            select(Batch)
            .where(
                Batch.item_id == batch.item_id,
                Batch.status == BatchStatus.ACTIVE,
                Batch.quantity_available > 0,
                Batch.expiration_date < batch.expiration_date,
                Batch.expiration_date >= today,
                Batch.id != batch_id,
            )
            .order_by(Batch.expiration_date.asc())
        )
        earlier = list(earlier_batches.scalars().all())
        
        if earlier:
            earliest = earlier[0]
            warnings.append(
                f"שים לב: קיימת אצווה {earliest.batch_number} עם תפוגה מוקדמת יותר "
                f"({earliest.expiration_date.strftime('%d/%m/%Y')})"
            )
        
        # Add expiration warnings
        warning_level = self._get_warning_level(days_until)
        if warning_level == "critical":
            warnings.append(f"אזהרה: אצווה תפוג תוקף תוך {days_until} ימים!")
        elif warning_level == "warning":
            warnings.append(f"שים לב: אצווה תפוג תוקף תוך {days_until} ימים")
        
        return PickingValidation(
            is_valid=True,
            batch_id=batch_id,
            quantity=quantity,
            errors=errors,
            warnings=warnings,
        )
    
    async def get_expiration_summary(self, item_id: UUID) -> dict:
        """
        Get expiration breakdown for an item's inventory.
        """
        batches = await self.get_available_batches(item_id, exclude_expired=False)
        today = date.today()
        
        summary = {
            "total_quantity": Decimal("0"),
            "total_batches": 0,
            "expired": {"quantity": Decimal("0"), "batches": 0},
            "critical": {"quantity": Decimal("0"), "batches": 0},
            "warning": {"quantity": Decimal("0"), "batches": 0},
            "caution": {"quantity": Decimal("0"), "batches": 0},
            "safe": {"quantity": Decimal("0"), "batches": 0},
        }
        
        for batch in batches:
            days_until = (batch.expiration_date - today).days
            level = self._get_warning_level(days_until)
            
            summary["total_quantity"] += batch.quantity_available
            summary["total_batches"] += 1
            
            if level in summary:
                summary[level]["quantity"] += batch.quantity_available
                summary[level]["batches"] += 1
        
        return summary

