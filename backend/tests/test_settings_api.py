"""Tests for settings API endpoints"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_email_settings_unauthorized(client: AsyncClient):
    """Test getting email settings without auth"""
    response = await client.get("/api/v1/settings/email")
    assert response.status_code in [401, 403]  # Either unauthorized or forbidden


@pytest.mark.asyncio
async def test_get_email_settings_as_manager(
    client: AsyncClient,
    auth_headers: dict
):
    """Test getting email settings as manager"""
    response = await client.get(
        "/api/v1/settings/email",
        headers=auth_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert "email_configured" in data
    assert "smtp_host" in data
    assert "smtp_port" in data
    assert "email_from" in data


@pytest.mark.asyncio
async def test_get_email_settings_as_admin(
    client: AsyncClient,
    admin_headers: dict
):
    """Test getting email settings as admin"""
    response = await client.get(
        "/api/v1/settings/email",
        headers=admin_headers
    )
    
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data["email_configured"], bool)


@pytest.mark.asyncio
async def test_send_test_email_unauthorized(client: AsyncClient):
    """Test sending test email without auth"""
    response = await client.post(
        "/api/v1/settings/email/test",
        json={"email": "test@example.com"}
    )
    assert response.status_code in [401, 403]  # Either unauthorized or forbidden


@pytest.mark.asyncio
@patch('app.services.email_service.aiosmtplib.send')
@patch('app.services.email_service.settings.smtp_user', 'test@example.com')
@patch('app.services.email_service.settings.smtp_password', 'testpass')
async def test_send_test_email_success(
    mock_send,
    client: AsyncClient,
    admin_headers: dict
):
    """Test sending test email successfully"""
    mock_send.return_value = None
    
    response = await client.post(
        "/api/v1/settings/email/test",
        headers=admin_headers,
        json={"email": "recipient@example.com"}
    )
    
    assert response.status_code == 200
    data = response.json()
    assert data["success"] is True
    assert "Test email sent" in data["message"]


@pytest.mark.asyncio
async def test_send_test_email_not_configured(
    client: AsyncClient,
    admin_headers: dict
):
    """Test sending test email when not configured"""
    response = await client.post(
        "/api/v1/settings/email/test",
        headers=admin_headers,
        json={"email": "test@example.com"}
    )
    
    # Should return 400 if email not configured
    assert response.status_code in [400, 500]


@pytest.mark.asyncio
async def test_send_test_email_invalid_email(
    client: AsyncClient,
    admin_headers: dict
):
    """Test sending test email with invalid email"""
    response = await client.post(
        "/api/v1/settings/email/test",
        headers=admin_headers,
        json={"email": "invalid-email"}
    )
    
    assert response.status_code == 422  # Validation error
