"""Goods Receipt service for receiving inventory"""
from datetime import date, datetime, timezone
from decimal import Decimal
from typing import Optional
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.location import Location
from app.models.movement import Movement, MovementType
from app.schemas.batch import BatchCreate
from app.services.sequence_service import generate_sequential_number
from app.services.system_settings_service import get_or_create_system_settings


class ReceivingService:
    """Service for goods receipt operations"""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _min_shelf_life_days(self) -> int:
        """Goods with less shelf life remaining than this cannot be received
        at all (hard block) - see validate_expiration_warning below for the
        separate, non-blocking "heads up" tiers. Backed by the SystemSettings
        singleton (editable via PUT /settings/system) rather than a hardcoded
        constant, so the frontend's pre-submit check (which reads the same
        row via systemSettingsApi.get()) can't silently drift out of sync."""
        row = await get_or_create_system_settings(self.db)
        return row.min_shelf_life_days

    async def generate_batch_number(self, prefix: str = "GR") -> str:
        """Generate unique batch number: GR-YYMMDD-XXX"""
        return await generate_sequential_number(self.db, Batch.batch_number, prefix, pad_width=3)

    async def generate_grn_number(self) -> str:
        """Generate Goods Receipt Note number"""
        return await self.generate_batch_number(prefix="GRN")

    async def _create_batch_with_generated_number(
        self,
        prefix: str = "GR",
        max_attempts: int = 5,
        **batch_kwargs,
    ) -> Batch:
        """Create and flush a Batch whose batch_number is auto-generated,
        retrying with a freshly generated number if a concurrent request
        already claimed the one we picked (batch_number is unique). Uses a
        SAVEPOINT so only this insert is rolled back on conflict, not the
        whole transaction - receive_multiple may have already flushed
        earlier items in the same session."""
        last_error: Optional[IntegrityError] = None
        for _ in range(max_attempts):
            batch_number = await self.generate_batch_number(prefix)
            batch = Batch(batch_number=batch_number, **batch_kwargs)
            try:
                async with self.db.begin_nested():
                    self.db.add(batch)
                    await self.db.flush()
                return batch
            except IntegrityError as exc:
                last_error = exc
                self.db.expunge(batch)
        raise ValueError(
            "לא ניתן ליצור מספר אצווה ייחודי, נסה שוב"  # Could not generate a unique batch number, please retry
        ) from last_error
    
    async def validate_item(self, item_id: UUID) -> Item:
        """Validate item exists"""
        result = await self.db.execute(
            select(Item).where(Item.id == item_id)
        )
        item = result.scalar_one_or_none()
        
        if not item:
            raise ValueError(f"פריט לא נמצא")  # Item not found
        
        return item
    
    async def validate_location(self, location_id: UUID) -> Location:
        """Validate location exists and is active"""
        result = await self.db.execute(
            select(Location).where(
                Location.id == location_id,
                Location.is_active == True
            )
        )
        location = result.scalar_one_or_none()
        
        if not location:
            raise ValueError(f"מיקום לא נמצא או לא פעיל")  # Location not found or inactive
        
        return location
    
    async def receive_goods(
        self,
        item_id: UUID,
        quantity: Decimal,
        expiration_date: date,
        user_id: UUID,
        batch_number: Optional[str] = None,
        supplier_batch_number: Optional[str] = None,
        location_id: Optional[UUID] = None,
        receipt_date: Optional[date] = None,
        notes: Optional[str] = None,
        manufacturing_date: Optional[date] = None,
    ) -> tuple[Batch, Movement, str]:
        """
        Receive goods into inventory
        
        Returns: (batch, movement, grn_number)
        """
        # Validate item
        item = await self.validate_item(item_id)
        
        # Validate location if provided
        if location_id:
            await self.validate_location(location_id)
        
        # Validate expiration date
        today = date.today()
        if expiration_date < today:
            raise ValueError("תאריך תפוגה לא יכול להיות בעבר")  # Expiration date cannot be in the past
        min_shelf_life_days = await self._min_shelf_life_days()
        if (expiration_date - today).days < min_shelf_life_days:
            raise ValueError(
                f"לא ניתן לקלוט - נותרו פחות מ-{min_shelf_life_days} ימים עד לתפוגה"
            )  # Cannot receive - less than {N} days remain until expiration

        # Validate quantity
        if quantity <= 0:
            raise ValueError("כמות חייבת להיות חיובית")  # Quantity must be positive
        
        # Generate GRN number
        grn_number = await self.generate_grn_number()

        batch_kwargs = dict(
            item_id=item_id,
            supplier_batch_number=supplier_batch_number,
            quantity_received=quantity,
            quantity_available=quantity,
            receipt_date=receipt_date or today,
            expiration_date=expiration_date,
            manufacturing_date=manufacturing_date,
            location_id=location_id,
            status=BatchStatus.ACTIVE,
            notes=notes,
        )

        if not batch_number:
            # Auto-generated numbers retry on a concurrent collision
            # instead of raising an unhandled IntegrityError.
            batch = await self._create_batch_with_generated_number(
                prefix="GR", **batch_kwargs
            )
        else:
            # Explicitly-supplied numbers are checked up front - a
            # collision here is a real "already exists" error, not an
            # internal generation race to retry.
            result = await self.db.execute(
                select(Batch).where(Batch.batch_number == batch_number)
            )
            if result.scalar_one_or_none():
                raise ValueError(f"מספר אצווה {batch_number} כבר קיים")  # Batch number already exists
            batch = Batch(batch_number=batch_number, **batch_kwargs)
            self.db.add(batch)
            await self.db.flush()

        # Create receipt movement
        movement = Movement(
            batch_id=batch.id,
            user_id=user_id,
            movement_type=MovementType.RECEIPT,
            quantity=quantity,
            quantity_before=Decimal("0"),
            quantity_after=quantity,
            reference_number=grn_number,
            notes=f"קבלת סחורה: {item.sku} - {item.name}",
            timestamp=datetime.now(timezone.utc),
        )
        
        self.db.add(movement)
        await self.db.flush()
        
        return batch, movement, grn_number
    
    async def receive_multiple(
        self,
        receipts: list[dict],
        user_id: UUID,
    ) -> tuple[list[Batch], list[Movement], str]:
        """
        Receive multiple items in a single GRN
        
        receipts: list of dicts with keys:
            - item_id
            - quantity
            - expiration_date
            - batch_number (optional)
            - supplier_batch_number (optional)
            - location_id (optional)
            - notes (optional)
        """
        grn_number = await self.generate_grn_number()
        min_shelf_life_days = await self._min_shelf_life_days()
        batches = []
        movements = []

        for receipt in receipts:
            item = await self.validate_item(receipt["item_id"])

            if receipt.get("location_id"):
                await self.validate_location(receipt["location_id"])

            # Validate expiration
            expiration_date = receipt["expiration_date"]
            today = date.today()
            if expiration_date < today:
                raise ValueError(
                    f"תאריך תפוגה לא תקין עבור פריט {item.sku}"
                )
            if (expiration_date - today).days < min_shelf_life_days:
                raise ValueError(
                    f"לא ניתן לקלוט את פריט {item.sku} - נותרו פחות מ-{min_shelf_life_days} ימים עד לתפוגה"
                )  # Cannot receive item {sku} - less than {N} days remain until expiration

            quantity = Decimal(str(receipt["quantity"]))
            if quantity <= 0:
                raise ValueError(
                    f"כמות חייבת להיות חיובית עבור פריט {item.sku}"
                )  # Quantity must be positive for item {sku}

            batch_kwargs = dict(
                item_id=receipt["item_id"],
                supplier_batch_number=receipt.get("supplier_batch_number"),
                quantity_received=quantity,
                quantity_available=quantity,
                receipt_date=date.today(),
                expiration_date=expiration_date,
                location_id=receipt.get("location_id"),
                status=BatchStatus.ACTIVE,
                notes=receipt.get("notes"),
            )

            batch_number = receipt.get("batch_number")
            if not batch_number:
                # Auto-generated numbers retry on a concurrent collision
                # instead of raising an unhandled IntegrityError.
                batch = await self._create_batch_with_generated_number(
                    prefix="GR", **batch_kwargs
                )
            else:
                batch = Batch(batch_number=batch_number, **batch_kwargs)
                self.db.add(batch)
                await self.db.flush()

            movement = Movement(
                batch_id=batch.id,
                user_id=user_id,
                movement_type=MovementType.RECEIPT,
                quantity=quantity,
                quantity_before=Decimal("0"),
                quantity_after=quantity,
                reference_number=grn_number,
                notes=f"קבלת סחורה: {item.sku}",
                timestamp=datetime.now(timezone.utc),
            )
            
            self.db.add(movement)
            batches.append(batch)
            movements.append(movement)
        
        await self.db.flush()
        return batches, movements, grn_number
    
    def validate_expiration_warning(
        self,
        expiration_date: date,
        warning_threshold_days: int = 180
    ) -> dict:
        """
        Check if expiration date triggers a warning
        Returns warning info if applicable
        """
        days_until = (expiration_date - date.today()).days
        
        if days_until < 30:
            return {
                "level": "critical",
                "message": f"אזהרה: תאריך תפוגה קרוב מאוד ({days_until} ימים)",
                "days_until_expiration": days_until,
            }
        elif days_until < 60:
            return {
                "level": "warning",
                "message": f"שים לב: תאריך תפוגה תוך {days_until} ימים",
                "days_until_expiration": days_until,
            }
        elif days_until < warning_threshold_days:
            return {
                "level": "info",
                "message": f"תאריך תפוגה תוך {days_until} ימים",
                "days_until_expiration": days_until,
            }
        
        return None

