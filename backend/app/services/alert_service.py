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
from app.models.user import User
from app.core.config import settings
from app.services.stock_helpers import available_quantity


class AlertService:
    """Service for managing alerts and notifications"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        from app.services.email_service import email_service
        self._email_enabled = email_service.is_configured
    
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
        
        # Broadcast alert via WebSocket
        try:
            from app.core.websocket import manager
            await manager.send_alert({
                "id": str(alert.id),
                "type": alert.alert_type.value,
                "severity": alert.severity.value,
                "title": alert.title,
                "message": alert.message,
                "created_at": alert.created_at.isoformat() if alert.created_at else None
            })
        except Exception as e:
            print(f">> Failed to broadcast alert: {e}")
        
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
    
    async def get_unread_count(self, location_ids: Optional[List[UUID]] = None) -> int:
        """Get count of unread alerts.

        location_ids restricts to alerts whose batch sits at one of those
        locations (item-only alerts are excluded when scoped, since they
        aren't attributable to a single location) - None means unrestricted.
        """
        query = select(func.count(Alert.id)).where(
            Alert.is_read == False, Alert.is_dismissed == False
        )
        if location_ids is not None:
            query = query.join(Batch, Alert.batch_id == Batch.id).where(
                Batch.location_id.in_(location_ids)
            )
        result = await self.db.execute(query)
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
    
    async def mark_all_as_read(self, location_ids: Optional[List[UUID]] = None) -> int:
        """Mark all alerts as read, return count.

        location_ids restricts the bulk update to alerts whose batch sits
        at one of those locations, so a scoped user can't blanket-dismiss
        alerts outside their own view - None means unrestricted.
        """
        from sqlalchemy import update

        query = update(Alert).where(Alert.is_read == False)
        if location_ids is not None:
            query = query.where(
                Alert.batch_id.in_(
                    select(Batch.id).where(Batch.location_id.in_(location_ids))
                )
            )
        query = query.values(is_read=True)

        result = await self.db.execute(query)
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

        # Bands must partition batches by days-until-expiration, not overlap.
        # prev_days is the lower (exclusive) bound of each band - a batch
        # already caught by an earlier (smaller-days) band is excluded from
        # later bands, so it gets exactly one alert per run instead of one
        # per threshold it happens to fall under.
        prev_days = 0
        for days, severity, level_text in thresholds:
            threshold_date = today + timedelta(days=days)
            prev_threshold_date = today + timedelta(days=prev_days)

            result = await self.db.execute(
                select(Batch)
                .options(selectinload(Batch.item))
                .where(
                    Batch.status == BatchStatus.ACTIVE,
                    Batch.expiration_date <= threshold_date,
                    Batch.expiration_date > prev_threshold_date,
                )
            )
            batches = result.scalars().all()

            for batch in batches:
                days_left = (batch.expiration_date - today).days

                alert_type = (
                    AlertType.EXPIRATION_CRITICAL
                    if days_left <= 30
                    else AlertType.EXPIRATION_WARNING
                )

                # Check if an alert already exists for this batch at this
                # level. Must match on the same alert_type this iteration
                # will actually create (previously hardcoded to
                # EXPIRATION_WARNING, so it never matched the
                # EXPIRATION_CRITICAL alerts created for the 30-day band,
                # and duplicates were created on every run). Dedupes against
                # any not-yet-dismissed alert rather than "created today" -
                # the previous func.date(created_at) == today check also
                # depended on the DB dialect parsing the stored timestamp
                # string (works on Postgres, not reliably on SQLite), and
                # would have re-alerted daily for a batch the user hasn't
                # acted on yet.
                existing = await self.db.execute(
                    select(Alert)
                    .where(
                        Alert.batch_id == batch.id,
                        Alert.alert_type == alert_type,
                        Alert.severity == severity,
                        Alert.is_dismissed == False,
                    )
                )
                if existing.scalar_one_or_none():
                    continue

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
                
                # Send email notification for critical alerts
                if self._email_enabled and severity in [AlertSeverity.CRITICAL, AlertSeverity.WARNING]:
                    await self._send_expiration_email(batch, days_left, severity)

            prev_days = days

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
            # Capture quantity before marking as scrap (for email)
            lost_quantity = float(batch.quantity_available)

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
                    f"וסומנה אוטומטית כגריטה. כמות: {lost_quantity}"
                ),
                batch_id=batch.id,
                item_id=batch.item_id,
            )
            results.append((batch, alert))

            # Send email notification for expired batches
            if self._email_enabled:
                await self._send_expired_batch_email(batch, lost_quantity)

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
            available = available_quantity(item, today)

            if available < item.reorder_point:
                # Dedupe against any not-yet-dismissed low-stock alert for
                # this item, rather than "created today" - the latter
                # relied on func.date(created_at) == today, which depends
                # on the DB dialect parsing the stored timestamp string
                # (works on Postgres, not reliably on SQLite), and would
                # have re-alerted daily for an item nobody has acted on.
                existing = await self.db.execute(
                    select(Alert)
                    .where(
                        Alert.item_id == item.id,
                        Alert.alert_type == AlertType.LOW_STOCK,
                        Alert.is_dismissed == False,
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
                
                # Send email notification for low stock
                if self._email_enabled and severity == AlertSeverity.CRITICAL:
                    await self._send_low_stock_email(item, available)
        
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

                # Send email notification for dead stock
                if self._email_enabled:
                    await self._send_dead_stock_email(item, days_inactive, float(total_qty))

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
    
    async def _get_notification_recipients(self) -> list[str]:
        """Get email addresses of users who opted into notifications.

        Each user may have multiple comma-separated emails in notification_email.
        """
        result = await self.db.execute(
            select(User).where(
                User.is_active == True,
                User.email_notifications_enabled == True,
            )
        )
        users = result.scalars().all()
        recipients: list[str] = []
        for user in users:
            raw = user.notification_email or user.email
            for addr in raw.split(","):
                addr = addr.strip()
                if addr and addr not in recipients:
                    recipients.append(addr)
        return recipients

    async def _notify_recipients(self, log_label: str, send_one) -> None:
        """Send an email to every opted-in recipient via `send_one(email)`,
        isolating failures per recipient - one bad address or a single API
        error must not block the rest from being notified - and logging
        (never raising) on failure, since alert creation must succeed
        regardless of email delivery problems.

        The four `_send_*_email` methods below previously each
        reimplemented this recipient-loop + try/except independently, and
        two of them (`_send_expiration_email`, `_send_low_stock_email`)
        had no per-recipient isolation, so one failing address would have
        silently stopped every recipient after it from being notified.
        """
        try:
            recipients = await self._get_notification_recipients()
        except Exception as e:
            print(f">> Failed to load notification recipients for {log_label}: {e}")
            return

        for email in recipients:
            try:
                await send_one(email)
            except Exception as e:
                print(f">> Failed to send {log_label} email to {email}: {e}")

    async def _send_expiration_email(self, batch: Batch, days_left: int, severity: AlertSeverity):
        """Send expiration alert email to opted-in users"""
        from app.services.email_service import email_service

        async def send_one(email: str) -> None:
            await email_service.send_expiration_alert(
                to=email,
                batch_number=batch.batch_number,
                item_name=batch.item.name if batch.item else "Unknown",
                expiration_date=batch.expiration_date.strftime('%d/%m/%Y'),
                days_until_expiry=days_left,
                quantity_available=float(batch.quantity_available),
                severity=severity.value,
            )

        await self._notify_recipients("expiration", send_one)

    async def _send_low_stock_email(self, item: Item, current_quantity: float):
        """Send low stock alert email to opted-in users"""
        from app.services.email_service import email_service

        async def send_one(email: str) -> None:
            await email_service.send_low_stock_alert(
                to=email,
                item_name=item.name,
                sku=item.sku,
                current_quantity=current_quantity,
                reorder_point=item.reorder_point,
                min_stock=item.min_stock,
            )

        await self._notify_recipients("low stock", send_one)

    async def _send_expired_batch_email(self, batch: Batch, lost_quantity: float):
        """Send expired-batch alert email to opted-in users"""
        from app.services.email_service import email_service

        async def send_one(email: str) -> None:
            await email_service.send_expired_batch_alert(
                to=email,
                batch_number=batch.batch_number,
                item_name=batch.item.name if batch.item else "Unknown",
                expiration_date=batch.expiration_date.strftime('%d/%m/%Y'),
                quantity_available=lost_quantity,
            )

        await self._notify_recipients("expired batch", send_one)

    async def _send_dead_stock_email(self, item: Item, days_inactive: int, total_quantity: float):
        """Send dead-stock alert email to opted-in users"""
        from app.services.email_service import email_service

        async def send_one(email: str) -> None:
            await email_service.send_dead_stock_alert(
                to=email,
                item_name=item.name,
                sku=item.sku,
                days_inactive=days_inactive,
                total_quantity=total_quantity,
            )

        await self._notify_recipients("dead stock", send_one)
