"""Tests for email service"""
import pytest
from unittest.mock import AsyncMock, Mock, patch
from app.services.email_service import EmailService


@pytest.fixture
def email_service():
    """Create email service instance"""
    return EmailService()


@pytest.mark.asyncio
async def test_email_service_initialization(email_service):
    """Test email service initializes correctly"""
    assert email_service.smtp_host is not None
    assert email_service.smtp_port is not None
    assert email_service.email_from is not None


@pytest.mark.asyncio
async def test_render_template(email_service):
    """Test template rendering"""
    html = email_service.render_template(
        "test_email.html"
    )
    
    assert html is not None
    assert "מערכת ניהול מלאי דיו" in html
    assert "בדיקת חיבור" in html


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_email_success(mock_send, email_service):
    """Test successful email sending"""
    # Configure mock
    mock_send.return_value = None
    
    # Override SMTP credentials for test
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    
    await email_service.send_email(
        to="recipient@example.com",
        subject="Test Email",
        html_body="<p>Test content</p>",
        priority=True
    )
    
    # Verify send was called
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_send_email_no_config(email_service):
    """Test email sending when not configured"""
    # Clear SMTP credentials
    email_service.smtp_user = ""
    email_service.smtp_password = ""
    
    # Should not raise error, just skip
    await email_service.send_email(
        to="recipient@example.com",
        subject="Test Email",
        html_body="<p>Test content</p>"
    )


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_expiration_alert(mock_send, email_service):
    """Test sending expiration alert email"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    # Patch send_email to call immediately (priority=True)
    with patch.object(email_service, 'send_email') as mock_send_email:
        mock_send_email.return_value = None
        
        await email_service.send_expiration_alert(
            to="manager@example.com",
            batch_number="BATCH-001",
            item_name="Black Ink",
            expiration_date="31/12/2024",
            days_until_expiry=30,
            quantity_available=100.0,
            severity="CRITICAL"
        )
        
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_low_stock_alert(mock_send, email_service):
    """Test sending low stock alert email"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    with patch.object(email_service, 'send_email') as mock_send_email:
        mock_send_email.return_value = None
        
        await email_service.send_low_stock_alert(
            to="manager@example.com",
            item_name="Cyan Ink",
            sku="INK-C-001",
            current_quantity=5.0,
            reorder_point=10,
            min_stock=5
        )
        
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_delivery_note_email(mock_send, email_service):
    """Test sending delivery note email"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    with patch.object(email_service, 'send_email') as mock_send_email:
        mock_send_email.return_value = None
        
        await email_service.send_delivery_note_email(
            to="customer@example.com",
            customer_name="Test Customer",
            delivery_note_number="DN-001",
            issue_date="21/02/2026",
            items_count=5
        )
        
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_weekly_report(mock_send, email_service):
    """Test sending weekly report email"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    with patch.object(email_service, 'send_email') as mock_send_email:
        mock_send_email.return_value = None
        
        await email_service.send_weekly_report(
            to="manager@example.com",
            start_date="14/02/2026",
            end_date="21/02/2026",
            total_value=50000.0,
            at_risk_percentage=15.5,
            low_stock_count=3,
            movements_count=25,
            new_alerts_count=8
        )
        
        mock_send_email.assert_called_once()


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_send_test_email(mock_send, email_service):
    """Test sending test email"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    await email_service.send_test_email("test@example.com")
    
    mock_send.assert_called_once()


@pytest.mark.asyncio
async def test_email_worker_lifecycle(email_service):
    """Test email worker start and stop"""
    await email_service.start_worker()
    assert email_service._worker_task is not None
    
    await email_service.stop_worker()
    assert email_service._worker_task.cancelled() or email_service._worker_task.done()


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
async def test_email_queue_processing(mock_send, email_service):
    """Test email queue processing"""
    email_service.smtp_user = "test@example.com"
    email_service.smtp_password = "testpassword"
    mock_send.return_value = None
    
    # Start worker
    await email_service.start_worker()
    
    # Queue email (not priority)
    await email_service.send_email(
        to="test@example.com",
        subject="Queued Email",
        html_body="<p>Test</p>",
        priority=False
    )
    
    # Wait for queue to process
    await email_service._email_queue.join()
    
    # Stop worker
    await email_service.stop_worker()
    
    # Email should have been sent
    assert mock_send.call_count >= 1
