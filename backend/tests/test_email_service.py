"""Tests for email service (Resend)"""
import pytest
from unittest.mock import patch, MagicMock
from app.services.email_service import EmailService


@pytest.fixture
def email_svc():
    """Create email service instance."""
    svc = EmailService()
    return svc


@pytest.mark.asyncio
async def test_email_service_initialization(email_svc):
    assert email_svc.email_from is not None


@pytest.mark.asyncio
async def test_render_template(email_svc):
    html = email_svc.render_template("test_email.html")
    assert html is not None
    assert "בדיקת חיבור" in html


@pytest.mark.asyncio
@patch("app.services.email_service.resend.Emails.send")
async def test_send_email_success(mock_send, email_svc):
    mock_send.return_value = {"id": "test-id"}
    email_svc._configured = True

    await email_svc.send_email(
        to="recipient@example.com",
        subject="Test Email",
        html_body="<p>Test content</p>",
    )

    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_no_config(email_svc):
    email_svc._configured = False
    # Should not raise, just skip
    await email_svc.send_email(
        to="recipient@example.com",
        subject="Test Email",
        html_body="<p>Test content</p>",
    )


@pytest.mark.asyncio
async def test_send_expiration_alert(email_svc):
    with patch.object(email_svc, "send_email") as mock:
        mock.return_value = None
        await email_svc.send_expiration_alert(
            to="manager@example.com",
            batch_number="BATCH-001",
            item_name="Black Ink",
            expiration_date="31/12/2024",
            days_until_expiry=30,
            quantity_available=100.0,
            severity="CRITICAL",
        )
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_send_low_stock_alert(email_svc):
    with patch.object(email_svc, "send_email") as mock:
        mock.return_value = None
        await email_svc.send_low_stock_alert(
            to="manager@example.com",
            item_name="Cyan Ink",
            sku="INK-C-001",
            current_quantity=5.0,
            reorder_point=10,
            min_stock=5,
        )
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_send_delivery_note_email(email_svc):
    with patch.object(email_svc, "send_email") as mock:
        mock.return_value = None
        await email_svc.send_delivery_note_email(
            to="customer@example.com",
            customer_name="Test Customer",
            delivery_note_number="DN-001",
            issue_date="21/02/2026",
            items_count=5,
        )
        mock.assert_called_once()


@pytest.mark.asyncio
async def test_send_weekly_report(email_svc):
    with patch.object(email_svc, "send_email") as mock:
        mock.return_value = None
        await email_svc.send_weekly_report(
            to="manager@example.com",
            start_date="14/02/2026",
            end_date="21/02/2026",
            total_value=50000.0,
            at_risk_percentage=15.5,
            low_stock_count=3,
            movements_count=25,
            new_alerts_count=8,
        )
        mock.assert_called_once()


@pytest.mark.asyncio
@patch("app.services.email_service.resend.Emails.send")
async def test_send_test_email(mock_send, email_svc):
    mock_send.return_value = {"id": "test-id"}
    email_svc._configured = True

    await email_svc.send_test_email("test@example.com")
    mock_send.assert_called_once()
