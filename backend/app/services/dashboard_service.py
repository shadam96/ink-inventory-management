"""Dashboard service for KPIs and analytics"""
from datetime import date, timedelta
from decimal import Decimal
from typing import Dict, List, Any
from uuid import UUID

from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.batch import Batch, BatchStatus
from app.models.item import Item
from app.models.movement import Movement, MovementType
from app.models.alert import Alert
from app.models.delivery_note import DeliveryNote, DeliveryNoteStatus


class DashboardService:
    """Service for dashboard KPIs and analytics"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def get_inventory_value(self) -> Dict[str, Any]:
        """Calculate total inventory value"""
        result = await self.db.execute(
            select(Item).options(selectinload(Item.batches))
        )
        items = result.scalars().all()
        
        today = date.today()
        total_value = Decimal("0")
        total_quantity = Decimal("0")
        items_count = 0
        
        for item in items:
            active_qty = sum(
                b.quantity_available 
                for b in item.batches 
                if b.status == BatchStatus.ACTIVE and b.expiration_date >= today
            )
            if active_qty > 0:
                items_count += 1
                total_quantity += active_qty
                total_value += active_qty * item.cost_price
        
        return {
            "total_value": float(total_value),
            "total_quantity": float(total_quantity),
            "items_with_stock": items_count,
            "currency": "ILS",
        }
    
    async def get_inventory_distribution(self) -> List[Dict[str, Any]]:
        """Get inventory distribution by item (for pie chart)"""
        result = await self.db.execute(
            select(Item).options(selectinload(Item.batches))
        )
        items = result.scalars().all()
        
        today = date.today()
        distribution = []
        
        for item in items:
            active_qty = sum(
                b.quantity_available 
                for b in item.batches 
                if b.status == BatchStatus.ACTIVE and b.expiration_date >= today
            )
            if active_qty > 0:
                value = float(active_qty * item.cost_price)
                distribution.append({
                    "item_id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "quantity": float(active_qty),
                    "value": value,
                    "unit": item.unit_of_measure,
                })
        
        # Sort by value descending
        distribution.sort(key=lambda x: x["value"], reverse=True)
        return distribution
    
    async def get_expiration_risk_map(self) -> Dict[str, Any]:
        """Get expiration risk breakdown (for gauge/risk map)"""
        today = date.today()
        
        result = await self.db.execute(
            select(Batch)
            .options(selectinload(Batch.item))
            .where(
                Batch.status == BatchStatus.ACTIVE,
                Batch.quantity_available > 0,
            )
        )
        batches = result.scalars().all()
        
        risk_levels = {
            "expired": {"quantity": Decimal("0"), "value": Decimal("0"), "batches": 0},
            "critical": {"quantity": Decimal("0"), "value": Decimal("0"), "batches": 0},  # 0-30 days
            "warning": {"quantity": Decimal("0"), "value": Decimal("0"), "batches": 0},   # 31-60 days
            "caution": {"quantity": Decimal("0"), "value": Decimal("0"), "batches": 0},   # 61-90 days
            "safe": {"quantity": Decimal("0"), "value": Decimal("0"), "batches": 0},      # 90+ days
        }
        
        for batch in batches:
            days_until = (batch.expiration_date - today).days
            cost = batch.item.cost_price if batch.item else Decimal("0")
            value = batch.quantity_available * cost
            
            if days_until < 0:
                level = "expired"
            elif days_until <= 30:
                level = "critical"
            elif days_until <= 60:
                level = "warning"
            elif days_until <= 90:
                level = "caution"
            else:
                level = "safe"
            
            risk_levels[level]["quantity"] += batch.quantity_available
            risk_levels[level]["value"] += value
            risk_levels[level]["batches"] += 1
        
        # Convert to float for JSON
        for level in risk_levels:
            risk_levels[level]["quantity"] = float(risk_levels[level]["quantity"])
            risk_levels[level]["value"] = float(risk_levels[level]["value"])
        
        # Calculate percentages
        total_value = sum(r["value"] for r in risk_levels.values())
        if total_value > 0:
            for level in risk_levels:
                risk_levels[level]["percentage"] = round(
                    risk_levels[level]["value"] / total_value * 100, 1
                )
        else:
            for level in risk_levels:
                risk_levels[level]["percentage"] = 0
        
        return {
            "risk_levels": risk_levels,
            "total_value": float(total_value),
            "color_codes": {
                "expired": "#000000",   # Black
                "critical": "#DC2626",  # Red
                "warning": "#F59E0B",   # Yellow/Orange
                "caution": "#FBBF24",   # Light Yellow
                "safe": "#10B981",      # Green
            }
        }
    
    async def get_low_stock_items(self) -> List[Dict[str, Any]]:
        """Get items below reorder point"""
        result = await self.db.execute(
            select(Item).options(selectinload(Item.batches))
        )
        items = result.scalars().all()
        
        today = date.today()
        low_stock = []
        
        for item in items:
            available = sum(
                b.quantity_available 
                for b in item.batches 
                if b.status == BatchStatus.ACTIVE and b.expiration_date >= today
            )
            
            if available < item.reorder_point:
                low_stock.append({
                    "item_id": str(item.id),
                    "sku": item.sku,
                    "name": item.name,
                    "current_quantity": float(available),
                    "reorder_point": item.reorder_point,
                    "min_stock": item.min_stock,
                    "shortage": float(item.reorder_point - available),
                    "is_critical": available < item.min_stock,
                })
        
        # Sort by shortage descending
        low_stock.sort(key=lambda x: x["shortage"], reverse=True)
        return low_stock
    
    async def get_recent_activity(self, days: int = 7) -> Dict[str, Any]:
        """Get recent activity summary"""
        today = date.today()
        start_date = today - timedelta(days=days)
        
        # Get movements
        result = await self.db.execute(
            select(Movement)
            .where(func.date(Movement.timestamp) >= start_date)
        )
        movements = result.scalars().all()
        
        receipts = sum(
            m.quantity for m in movements if m.movement_type == MovementType.RECEIPT
        )
        dispatches = sum(
            m.quantity for m in movements if m.movement_type == MovementType.DISPATCH
        )
        scraps = sum(
            m.quantity for m in movements if m.movement_type == MovementType.SCRAP
        )
        
        # Get delivery notes
        result = await self.db.execute(
            select(func.count(DeliveryNote.id))
            .where(func.date(DeliveryNote.created_at) >= start_date)
        )
        delivery_notes_count = result.scalar() or 0
        
        # Get new alerts
        result = await self.db.execute(
            select(func.count(Alert.id))
            .where(func.date(Alert.created_at) >= start_date)
        )
        alerts_count = result.scalar() or 0
        
        return {
            "period_days": days,
            "start_date": start_date.isoformat(),
            "end_date": today.isoformat(),
            "receipts_quantity": float(receipts),
            "dispatches_quantity": float(dispatches),
            "scraps_quantity": float(scraps),
            "delivery_notes_created": delivery_notes_count,
            "alerts_generated": alerts_count,
            "movements_count": len(movements),
        }
    
    async def get_kpi_summary(self) -> Dict[str, Any]:
        """Get all KPIs for dashboard"""
        inventory = await self.get_inventory_value()
        risk_map = await self.get_expiration_risk_map()
        low_stock = await self.get_low_stock_items()
        activity = await self.get_recent_activity()
        
        # Unread alerts count
        result = await self.db.execute(
            select(func.count(Alert.id))
            .where(Alert.is_read == False, Alert.is_dismissed == False)
        )
        unread_alerts = result.scalar() or 0
        
        return {
            "inventory_value": inventory["total_value"],
            "items_in_stock": inventory["items_with_stock"],
            "at_risk_value": (
                risk_map["risk_levels"]["critical"]["value"] +
                risk_map["risk_levels"]["warning"]["value"]
            ),
            "at_risk_percentage": (
                risk_map["risk_levels"]["critical"]["percentage"] +
                risk_map["risk_levels"]["warning"]["percentage"]
            ),
            "low_stock_items": len(low_stock),
            "critical_low_stock": sum(1 for i in low_stock if i["is_critical"]),
            "unread_alerts": unread_alerts,
            "recent_receipts": activity["receipts_quantity"],
            "recent_dispatches": activity["dispatches_quantity"],
        }
