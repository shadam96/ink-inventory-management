"""Email service for sending notifications"""
import asyncio
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from pathlib import Path
from typing import List, Optional
import aiosmtplib
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings


# Setup Jinja2 for email templates
template_dir = Path(__file__).parent.parent / "templates" / "email"
template_dir.mkdir(parents=True, exist_ok=True)
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))


class EmailService:
    """Service for sending email notifications"""
    
    def __init__(self):
        self.smtp_host = settings.smtp_host
        self.smtp_port = settings.smtp_port
        self.smtp_user = settings.smtp_user
        self.smtp_password = settings.smtp_password
        self.email_from = settings.email_from
        self._email_queue: asyncio.Queue = asyncio.Queue()
        self._worker_task: Optional[asyncio.Task] = None
    
    async def start_worker(self):
        """Start background email worker"""
        if self._worker_task is None or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._email_worker())
    
    async def stop_worker(self):
        """Stop background email worker"""
        if self._worker_task and not self._worker_task.done():
            self._worker_task.cancel()
            try:
                await self._worker_task
            except asyncio.CancelledError:
                pass
    
    async def _email_worker(self):
        """Background worker to process email queue"""
        while True:
            try:
                email_data = await self._email_queue.get()
                await self._send_email_internal(**email_data)
                self._email_queue.task_done()
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f">> Email worker error: {e}")
                await asyncio.sleep(5)
    
    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        priority: bool = False
    ):
        """
        Queue an email to be sent
        
        Args:
            to: Recipient email address
            subject: Email subject
            html_body: HTML email body
            text_body: Plain text email body (optional)
            priority: If True, send immediately instead of queuing
        """
        if not self.smtp_user or not self.smtp_password:
            print(f">> Email not configured, skipping: {subject} to {to}")
            return
        
        email_data = {
            "to": to,
            "subject": subject,
            "html_body": html_body,
            "text_body": text_body
        }
        
        if priority:
            await self._send_email_internal(**email_data)
        else:
            await self._email_queue.put(email_data)
    
    async def _send_email_internal(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None
    ):
        """Internal method to send email via SMTP"""
        try:
            message = MIMEMultipart("alternative")
            message["From"] = self.email_from
            message["To"] = to
            message["Subject"] = subject
            
            # Add text and HTML parts
            if text_body:
                part1 = MIMEText(text_body, "plain", "utf-8")
                message.attach(part1)
            
            part2 = MIMEText(html_body, "html", "utf-8")
            message.attach(part2)
            
            # Send email
            await aiosmtplib.send(
                message,
                hostname=self.smtp_host,
                port=self.smtp_port,
                username=self.smtp_user,
                password=self.smtp_password,
                start_tls=True,
            )
            
            print(f">> Email sent: {subject} to {to}")
            
        except Exception as e:
            print(f">> Failed to send email: {e}")
            raise
    
    def render_template(self, template_name: str, **context) -> str:
        """Render an email template with context"""
        template = jinja_env.get_template(template_name)
        return template.render(**context)
    
    async def send_expiration_alert(
        self,
        to: str,
        batch_number: str,
        item_name: str,
        expiration_date: str,
        days_until_expiry: int,
        quantity_available: float,
        severity: str
    ):
        """Send expiration alert email"""
        subject = f"התראה: תוקף מלאי עומד לפוג - {item_name}"
        
        html_body = self.render_template(
            "expiration_alert.html",
            batch_number=batch_number,
            item_name=item_name,
            expiration_date=expiration_date,
            days_until_expiry=days_until_expiry,
            quantity_available=quantity_available,
            severity=severity
        )
        
        await self.send_email(to, subject, html_body)
    
    async def send_low_stock_alert(
        self,
        to: str,
        item_name: str,
        sku: str,
        current_quantity: float,
        reorder_point: int,
        min_stock: int
    ):
        """Send low stock alert email"""
        subject = f"התראה: מלאי נמוך - {item_name}"
        
        html_body = self.render_template(
            "low_stock_alert.html",
            item_name=item_name,
            sku=sku,
            current_quantity=current_quantity,
            reorder_point=reorder_point,
            min_stock=min_stock
        )
        
        await self.send_email(to, subject, html_body)
    
    async def send_delivery_note_email(
        self,
        to: str,
        customer_name: str,
        delivery_note_number: str,
        issue_date: str,
        items_count: int,
        pdf_path: Optional[str] = None
    ):
        """Send delivery note email to customer"""
        subject = f"תעודת משלוח {delivery_note_number} - {customer_name}"
        
        html_body = self.render_template(
            "delivery_note_email.html",
            customer_name=customer_name,
            delivery_note_number=delivery_note_number,
            issue_date=issue_date,
            items_count=items_count
        )
        
        await self.send_email(to, subject, html_body)
    
    async def send_weekly_report(
        self,
        to: str,
        start_date: str,
        end_date: str,
        total_value: float,
        at_risk_percentage: float,
        low_stock_count: int,
        movements_count: int,
        new_alerts_count: int
    ):
        """Send weekly inventory report"""
        subject = f"דוח מלאי שבועי - {start_date} עד {end_date}"
        
        html_body = self.render_template(
            "weekly_report.html",
            start_date=start_date,
            end_date=end_date,
            total_value=total_value,
            at_risk_percentage=at_risk_percentage,
            low_stock_count=low_stock_count,
            movements_count=movements_count,
            new_alerts_count=new_alerts_count
        )
        
        await self.send_email(to, subject, html_body)
    
    async def send_test_email(self, to: str):
        """Send test email"""
        subject = "בדיקת חיבור מערכת ניהול מלאי"
        
        html_body = self.render_template("test_email.html")
        
        await self.send_email(to, subject, html_body, priority=True)


# Global email service instance
email_service = EmailService()
