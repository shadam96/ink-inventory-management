"""Document generation service for delivery notes and reports"""
import io
from datetime import date, datetime
from decimal import Decimal
from typing import List, Optional
from uuid import UUID

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    Image,
)
from reportlab.lib.enums import TA_RIGHT, TA_CENTER, TA_LEFT
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.delivery_note import DeliveryNote, DeliveryNoteItem, DeliveryNoteStatus
from app.models.customer import Customer
from app.models.batch import Batch
from app.models.item import Item
from app.models.user import User


class DocumentService:
    """Service for generating PDF documents"""
    
    def __init__(self, db: AsyncSession):
        self.db = db
    
    async def generate_delivery_note_number(self) -> str:
        """Generate unique delivery note number: DN-YYMMDD-XXXX"""
        from sqlalchemy import func
        
        date_str = datetime.now().strftime("%y%m%d")
        prefix_pattern = f"DN-{date_str}-%"
        
        result = await self.db.execute(
            select(func.max(DeliveryNote.delivery_note_number))
            .where(DeliveryNote.delivery_note_number.like(prefix_pattern))
        )
        last_dn = result.scalar()
        
        if last_dn:
            try:
                last_seq = int(last_dn.split("-")[-1])
                next_seq = last_seq + 1
            except (ValueError, IndexError):
                next_seq = 1
        else:
            next_seq = 1
        
        return f"DN-{date_str}-{next_seq:04d}"
    
    async def create_delivery_note(
        self,
        customer_id: UUID,
        items: List[dict],  # [{"batch_id": UUID, "quantity": Decimal}]
        user_id: UUID,
        is_consignment: bool = False,
        notes: Optional[str] = None,
        issue_date: Optional[date] = None,
    ) -> DeliveryNote:
        """Create a new delivery note"""
        # Validate customer
        result = await self.db.execute(
            select(Customer).where(Customer.id == customer_id)
        )
        customer = result.scalar_one_or_none()
        if not customer:
            raise ValueError("לקוח לא נמצא")
        
        # Generate DN number
        dn_number = await self.generate_delivery_note_number()
        
        # Create delivery note
        delivery_note = DeliveryNote(
            delivery_note_number=dn_number,
            customer_id=customer_id,
            created_by=user_id,
            status=DeliveryNoteStatus.DRAFT,
            is_consignment=is_consignment,
            notes=notes,
            issue_date=issue_date or date.today(),
        )
        
        self.db.add(delivery_note)
        await self.db.flush()
        
        # Add items
        for item_data in items:
            # Get batch to find item_id
            result = await self.db.execute(
                select(Batch).where(Batch.id == item_data["batch_id"])
            )
            batch = result.scalar_one_or_none()
            if not batch:
                raise ValueError(f"אצווה לא נמצאה: {item_data['batch_id']}")
            
            dn_item = DeliveryNoteItem(
                delivery_note_id=delivery_note.id,
                item_id=batch.item_id,
                batch_id=item_data["batch_id"],
                quantity=item_data["quantity"],
            )
            self.db.add(dn_item)
        
        await self.db.flush()
        return delivery_note
    
    async def get_delivery_note_with_details(
        self,
        delivery_note_id: UUID
    ) -> Optional[DeliveryNote]:
        """Get delivery note with all related data"""
        result = await self.db.execute(
            select(DeliveryNote)
            .options(
                selectinload(DeliveryNote.customer),
                selectinload(DeliveryNote.created_by_user),
                selectinload(DeliveryNote.items)
                .selectinload(DeliveryNoteItem.item),
                selectinload(DeliveryNote.items)
                .selectinload(DeliveryNoteItem.batch),
            )
            .where(DeliveryNote.id == delivery_note_id)
        )
        return result.scalar_one_or_none()
    
    async def generate_delivery_note_pdf(
        self,
        delivery_note_id: UUID
    ) -> bytes:
        """Generate PDF for a delivery note"""
        dn = await self.get_delivery_note_with_details(delivery_note_id)
        if not dn:
            raise ValueError("תעודת משלוח לא נמצאה")
        
        # Create PDF buffer
        buffer = io.BytesIO()
        
        # Create document
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20*mm,
            leftMargin=20*mm,
            topMargin=20*mm,
            bottomMargin=20*mm,
        )
        
        # Styles
        styles = getSampleStyleSheet()
        
        # Custom styles for RTL Hebrew support
        title_style = ParagraphStyle(
            'Title',
            parent=styles['Heading1'],
            fontSize=18,
            alignment=TA_CENTER,
            spaceAfter=20,
        )
        
        header_style = ParagraphStyle(
            'Header',
            parent=styles['Normal'],
            fontSize=12,
            alignment=TA_RIGHT,
        )
        
        # Build document elements
        elements = []
        
        # Title
        if dn.is_consignment:
            title = "תעודת משלוח - העברה לקונסיגנציה"
        else:
            title = "תעודת משלוח"
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 10*mm))
        
        # Header info
        header_data = [
            ["מספר תעודה:", dn.delivery_note_number],
            ["תאריך:", dn.issue_date.strftime("%d/%m/%Y") if dn.issue_date else ""],
            ["לקוח:", dn.customer.name if dn.customer else ""],
            ["כתובת:", dn.customer.address if dn.customer and dn.customer.address else ""],
            ["איש קשר:", dn.customer.contact_person if dn.customer and dn.customer.contact_person else ""],
        ]
        
        header_table = Table(header_data, colWidths=[40*mm, 120*mm])
        header_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (0, -1), 'RIGHT'),
            ('ALIGN', (1, 0), (1, -1), 'LEFT'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(header_table)
        elements.append(Spacer(1, 10*mm))
        
        # Items table
        items_header = ["#", "מק\"ט", "תיאור", "אצווה", "תפוגה", "כמות", "יח'"]
        items_data = [items_header]
        
        for i, item in enumerate(dn.items, 1):
            items_data.append([
                str(i),
                item.item.sku if item.item else "",
                item.item.name if item.item else "",
                item.batch.batch_number if item.batch else "",
                item.batch.expiration_date.strftime("%d/%m/%Y") if item.batch else "",
                f"{item.quantity:.2f}",
                item.item.unit_of_measure if item.item else "",
            ])
        
        # Add total row
        total_qty = sum(item.quantity for item in dn.items)
        items_data.append(["", "", "", "", "סה\"כ:", f"{total_qty:.2f}", ""])
        
        items_table = Table(
            items_data,
            colWidths=[10*mm, 25*mm, 50*mm, 30*mm, 25*mm, 20*mm, 15*mm]
        )
        items_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 9),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('ALIGN', (5, 1), (5, -1), 'CENTER'),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -2), 0.5, colors.black),
            ('LINEABOVE', (4, -1), (-1, -1), 1, colors.black),
            ('FONTSIZE', (4, -1), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 5),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(items_table)
        elements.append(Spacer(1, 15*mm))
        
        # Notes
        if dn.notes:
            elements.append(Paragraph(f"הערות: {dn.notes}", header_style))
            elements.append(Spacer(1, 10*mm))
        
        # Signature area
        sig_data = [
            ["חתימת מקבל:", "_________________", "תאריך:", "_________________"],
            ["שם מקבל:", "_________________", "", ""],
        ]
        sig_table = Table(sig_data, colWidths=[30*mm, 50*mm, 25*mm, 50*mm])
        sig_table.setStyle(TableStyle([
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('TOPPADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(sig_table)
        
        # Footer
        elements.append(Spacer(1, 20*mm))
        footer_text = f"הופק על ידי: {dn.created_by_user.full_name if dn.created_by_user else ''}"
        elements.append(Paragraph(footer_text, header_style))
        
        # Build PDF
        doc.build(elements)
        
        # Get PDF bytes
        pdf_bytes = buffer.getvalue()
        buffer.close()
        
        return pdf_bytes
    
    async def update_delivery_note_status(
        self,
        delivery_note_id: UUID,
        new_status: DeliveryNoteStatus,
    ) -> DeliveryNote:
        """Update delivery note status"""
        result = await self.db.execute(
            select(DeliveryNote).where(DeliveryNote.id == delivery_note_id)
        )
        dn = result.scalar_one_or_none()
        
        if not dn:
            raise ValueError("תעודת משלוח לא נמצאה")
        
        dn.status = new_status
        
        if new_status == DeliveryNoteStatus.ISSUED and not dn.issue_date:
            dn.issue_date = date.today()
        
        if new_status == DeliveryNoteStatus.DELIVERED and not dn.delivery_date:
            dn.delivery_date = date.today()
        
        await self.db.flush()
        return dn
