"""Email service using Resend for transactional emails"""
import logging
from pathlib import Path
from typing import Optional

import resend
from jinja2 import Environment, FileSystemLoader

from app.core.config import settings

logger = logging.getLogger(__name__)

# Setup Jinja2 for email templates
template_dir = Path(__file__).parent.parent / "templates" / "email"
template_dir.mkdir(parents=True, exist_ok=True)
jinja_env = Environment(loader=FileSystemLoader(str(template_dir)))


class EmailService:
    """Transactional email service backed by Resend."""

    def __init__(self):
        self.api_key = settings.resend_api_key
        self.email_from = settings.email_from
        self._configured = False
        if self.api_key:
            resend.api_key = self.api_key
            self._configured = True
            logger.info("Email service configured (Resend)")
        else:
            logger.warning("RESEND_API_KEY not set — emails will be skipped")

    @property
    def is_configured(self) -> bool:
        return self._configured

    async def send_email(
        self,
        to: str,
        subject: str,
        html_body: str,
        text_body: Optional[str] = None,
        priority: bool = False,  # kept for API compat, ignored
    ):
        """Send an email via Resend. Fires immediately — no queue."""
        if not self._configured:
            logger.warning("Email skipped (not configured): %s -> %s", subject, to)
            return

        try:
            params: resend.Emails.SendParams = {
                "from": self.email_from,
                "to": [to],
                "subject": subject,
                "html": html_body,
            }
            if text_body:
                params["text"] = text_body

            resend.Emails.send(params)
            logger.info("Email sent: %s -> %s", subject, to)
        except Exception:
            logger.exception("Failed to send email: %s -> %s", subject, to)
            raise

    def render_template(self, template_name: str, **context) -> str:
        """Render an email template with context."""
        template = jinja_env.get_template(template_name)
        return template.render(**context)

    # ------------------------------------------------------------------
    # Convenience methods (unchanged public API)
    # ------------------------------------------------------------------

    async def send_expiration_alert(
        self,
        to: str,
        batch_number: str,
        item_name: str,
        expiration_date: str,
        days_until_expiry: int,
        quantity_available: float,
        severity: str,
    ):
        subject = f"התראה: תוקף מלאי עומד לפוג - {item_name}"
        html_body = self.render_template(
            "expiration_alert.html",
            batch_number=batch_number,
            item_name=item_name,
            expiration_date=expiration_date,
            days_until_expiry=days_until_expiry,
            quantity_available=quantity_available,
            severity=severity,
        )
        await self.send_email(to, subject, html_body)

    async def send_low_stock_alert(
        self,
        to: str,
        item_name: str,
        sku: str,
        current_quantity: float,
        reorder_point: int,
        min_stock: int,
    ):
        subject = f"התראה: מלאי נמוך - {item_name}"
        html_body = self.render_template(
            "low_stock_alert.html",
            item_name=item_name,
            sku=sku,
            current_quantity=current_quantity,
            reorder_point=reorder_point,
            min_stock=min_stock,
        )
        await self.send_email(to, subject, html_body)

    async def send_expired_batch_alert(
        self,
        to: str,
        batch_number: str,
        item_name: str,
        expiration_date: str,
        quantity_available: float,
    ):
        subject = f"אצווה פגת תוקף - {item_name}"
        html_body = self.render_template(
            "expired_batch_alert.html",
            batch_number=batch_number,
            item_name=item_name,
            expiration_date=expiration_date,
            quantity_available=quantity_available,
        )
        await self.send_email(to, subject, html_body)

    async def send_dead_stock_alert(
        self,
        to: str,
        item_name: str,
        sku: str,
        days_inactive: int,
        total_quantity: float,
    ):
        subject = f"מלאי מת - {item_name}"
        html_body = self.render_template(
            "dead_stock_alert.html",
            item_name=item_name,
            sku=sku,
            days_inactive=days_inactive,
            total_quantity=total_quantity,
        )
        await self.send_email(to, subject, html_body)

    async def send_delivery_note_email(
        self,
        to: str,
        customer_name: str,
        delivery_note_number: str,
        issue_date: str,
        items_count: int,
        pdf_path: Optional[str] = None,
    ):
        subject = f"תעודת משלוח {delivery_note_number} - {customer_name}"
        html_body = self.render_template(
            "delivery_note_email.html",
            customer_name=customer_name,
            delivery_note_number=delivery_note_number,
            issue_date=issue_date,
            items_count=items_count,
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
        new_alerts_count: int,
    ):
        subject = f"דוח מלאי שבועי - {start_date} עד {end_date}"
        html_body = self.render_template(
            "weekly_report.html",
            start_date=start_date,
            end_date=end_date,
            total_value=total_value,
            at_risk_percentage=at_risk_percentage,
            low_stock_count=low_stock_count,
            movements_count=movements_count,
            new_alerts_count=new_alerts_count,
        )
        await self.send_email(to, subject, html_body)

    async def send_test_email(self, to: str):
        subject = "בדיקת חיבור מערכת ניהול מלאי"
        html_body = self.render_template("test_email.html")
        await self.send_email(to, subject, html_body)


# Global email service instance
email_service = EmailService()
