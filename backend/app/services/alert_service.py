"""Alert service for notifications and warnings"""
from datetime import date, datetime, timedelta, timezone
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.alert import Alert, AlertType, AlertSeverity
from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement
from app.core.config import settings


class AlertService:
    """Service for managing alerts and notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def create_alert(
        self,
        alert_type: AlertType,
        severity: AlertSeverity,
        title: str,
        message: str,
        batch_id: Optional[UUID] = None,
        item_id: Optional[UUID] = None,
    ) -> Alert:
        """Create a new alert"""
        alert = Alert(
            alert_type=alert_type,
            severity=severity,
            title=title,
            message=message,
            batch_id=batch_id,
            item_id=item_id,
            is_read=False,
            is_dismissed=False,
        )
        self.db.add(alert)
        await self.db.flush()
        return alert
    
    async def get_unread_alerts(
        self,
        limit: int = 50,
        alert_type: Optional[AlertType] = None,
    ) -> List[Alert]:
        """Get unread alerts"""
        query = (
            select(Alert)
            .where(Alert.is_read == False, Alert.is_dismissed == False)
            .order_by(Alert.created_at.desc())
            .limit(limit)
        )
        
        if alert_type:
            query = query.where(Alert.alert_type == alert_type)
        
        result = await self.db.execute(query)
        return list(result.scalars().all())
    
    async def get_unread_count(self) -> int:
        """Get count of unread alerts"""
        result = await self.db.execute(
            select(func.count(Alert.id))
            .where(Alert.is_read == False, Alert.is_dismissed == False)
        )
        return result.scalar() or 0
    
    async def mark_as_read(self, alert_id: UUID) -> None:
        """Mark an alert as read"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_read = True
            await self.db.flush()
    
    async def mark_all_as_read(self) -> int:
        """Mark all alerts as read, return count"""
        from sqlalchemy import update
        
        result = await self.db.execute(
            update(Alert)
            .where(Alert.is_read == False)
            .values(is_read=True)
        )
        await self.db.flush()
        return result.rowcount
    
    async def dismiss_alert(self, alert_id: UUID) -> None:
        """Dismiss an alert"""
        result = await self.db.execute(
            select(Alert).where(Alert.id == alert_id)
        )
        alert = result.scalar_one_or_none()
        if alert:
            alert.is_dismissed = True
            await self.db.flush()
    
    async def check_expiring_batches(self) -> List[Alert]:
        """
        Check for batches approaching expiration and create alerts.
        Uses configurable thresholds: 120, 90, 60, 30 days.
        """
        today = date.today()
        alerts_created = []
        
        thresholds = [
            (settings.alert_threshold_30, AlertSeverity.CRITICAL, "קריטי"),
            (settings.alert_threshold_60, AlertSeverity.WARNING, "אזהרה"),
            (settings.alert_threshold_90, AlertSeverity.WARNING, "שים לב"),
            (settings.alert_threshold_120, AlertSeverity.INFO, "מידע"),
        ]
        
        for days, severity, level_text in thresholds:
            threshold_date = today + timedelta(days=days)
            prev_threshold = today + timedelta(days=days + 1)
            
            # Find batches expiring exactly at this threshold
            result = await self.db.execute(
                select(Batch)
                .options(selectinload(Batch.item))
                .where(
                    Batch.status == BatchStatus.ACTIVE,
                    Batch.expiration_date <= threshold_date,
                    Batch.expiration_date > today,
                )
            )
            batches = result.scalars().all()
            
            for batch in batches:
                days_left = (batch.expiration_date - today).days
                
                # Check if alert already exists for this batch at this level
                existing = await self.db.execute(
                    select(Alert)
                    .where(
                        Alert.batch_id == batch.id,
                        Alert.alert_type == AlertType.EXPIRATION_WARNING,
                        Alert.severity == severity,
                        func.date(Alert.created_at) == today,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                alert_type = (
                    AlertType.EXPIRATION_CRITICAL 
                    if days_left <= 30 
                    else AlertType.EXPIRATION_WARNING
                )
                
                alert = await self.create_alert(
                    alert_type=alert_type,
                    severity=severity,
                    title=f"{level_text}: אצווה מתקרבת לתפוגה",
                    message=(
                        f"אצווה {batch.batch_number} של {batch.item.name if batch.item else 'פריט'} "
                        f"תפוג תוקף ב-{batch.expiration_date.strftime('%d/%m/%Y')} "
                        f"({days_left} ימים)"
                    ),
                    batch_id=batch.id,
                    item_id=batch.item_id,
                )
                alerts_created.append(alert)
        
        return alerts_created
    
    async def check_expired_batches(self) -> List[tuple[Batch, Alert]]:
        """
        Check for expired batches, mark as scrap, and create alerts.
        """
        today = date.today()
        results = []
        
        # Find expired active batches
        result = await self.db.execute(
            select(Batch)
            .options(selectinload(Batch.item))
            .where(
                Batch.status == BatchStatus.ACTIVE,
                Batch.expiration_date < today,
            )
        )
        expired_batches = result.scalars().all()
        
        for batch in expired_batches:
            # Mark as scrap
            batch.status = BatchStatus.SCRAP
            batch.notes = f"{batch.notes or ''}\nסומן כגריטה אוטומטית עקב פג תוקף: {today}".strip()
            
            # Create alert
            alert = await self.create_alert(
                alert_type=AlertType.EXPIRED,
                severity=AlertSeverity.CRITICAL,
                title="אצווה פגת תוקף - סומנה כגריטה",
                message=(
                    f"אצווה {batch.batch_number} של {batch.item.name if batch.item else 'פריט'} "
                    f"פגה תוקפה ב-{batch.expiration_date.strftime('%d/%m/%Y')} "
                    f"וסומנה אוטומטית כגריטה. כמות: {batch.quantity_available}"
                ),
                batch_id=batch.id,
                item_id=batch.item_id,
            )
            results.append((batch, alert))
        
        await self.db.flush()
        return results
    
    async def check_low_stock(self) -> List[Alert]:
        """Check for items below reorder point"""
        alerts_created = []
        
        # Get all items with their active batches
        result = await self.db.execute(
            select(Item).options(selectinload(Item.batches))
        )
        items = result.scalars().all()
        
        today = date.today()
        
        for item in items:
            # Calculate available stock (non-expired, active batches)
            available = sum(
                b.quantity_available 
                for b in item.batches 
                if b.status == BatchStatus.ACTIVE and b.expiration_date >= today
            )
            
            if available < item.reorder_point:
                # Check for existing alert today
                existing = await self.db.execute(
                    select(Alert)
                    .where(
                        Alert.item_id == item.id,
                        Alert.alert_type == AlertType.LOW_STOCK,
                        func.date(Alert.created_at) == today,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                severity = (
                    AlertSeverity.CRITICAL 
                    if available < item.min_stock 
                    else AlertSeverity.WARNING
                )
                
                alert = await self.create_alert(
                    alert_type=AlertType.LOW_STOCK,
                    severity=severity,
                    title=f"מלאי נמוך: {item.sku}",
                    message=(
                        f"מלאי של {item.name} ({item.sku}) ירד מתחת לנקודת ההזמנה. "
                        f"כמות נוכחית: {available}, נקודת הזמנה: {item.reorder_point}"
                    ),
                    item_id=item.id,
                )
                alerts_created.append(alert)
        
        return alerts_created
    
    async def check_dead_stock(self) -> List[Alert]:
        """Check for items with no movement for extended period"""
        alerts_created = []
        today = date.today()
        threshold_date = today - timedelta(days=settings.dead_stock_days)
        
        # Get items with active batches
        result = await self.db.execute(
            select(Item)
            .options(selectinload(Item.batches))
        )
        items = result.scalars().all()
        
        for item in items:
            active_batches = [
                b for b in item.batches 
                if b.status == BatchStatus.ACTIVE
            ]
            
            if not active_batches:
                continue
            
            # Check last movement for any batch of this item
            batch_ids = [b.id for b in active_batches]
            result = await self.db.execute(
                select(func.max(Movement.timestamp))
                .where(Movement.batch_id.in_(batch_ids))
            )
            last_movement = result.scalar()
            
            if last_movement and last_movement.date() < threshold_date:
                # Check for existing alert this week
                week_ago = today - timedelta(days=7)
                existing = await self.db.execute(
                    select(Alert)
                    .where(
                        Alert.item_id == item.id,
                        Alert.alert_type == AlertType.DEAD_STOCK,
                        func.date(Alert.created_at) >= week_ago,
                    )
                )
                if existing.scalar_one_or_none():
                    continue
                
                days_inactive = (today - last_movement.date()).days
                total_qty = sum(b.quantity_available for b in active_batches)
                
                alert = await self.create_alert(
                    alert_type=AlertType.DEAD_STOCK,
                    severity=AlertSeverity.WARNING,
                    title=f"מלאי מת: {item.sku}",
                    message=(
                        f"פריט {item.name} ({item.sku}) לא זז מהמחסן "
                        f"{days_inactive} ימים. כמות במלאי: {total_qty}"
                    ),
                    item_id=item.id,
                )
                alerts_created.append(alert)
        
        return alerts_created
    
    async def run_all_checks(self) -> dict:
        """Run all alert checks and return summary"""
        expiring = await self.check_expiring_batches()
        expired = await self.check_expired_batches()
        low_stock = await self.check_low_stock()
        dead_stock = await self.check_dead_stock()
        
        await self.db.commit()
        
        return {
            "expiring_alerts": len(expiring),
            "expired_batches": len(expired),
            "low_stock_alerts": len(low_stock),
            "dead_stock_alerts": len(dead_stock),
            "total_new_alerts": len(expiring) + len(expired) + len(low_stock) + len(dead_stock),
        }
