"""Tests for settings API endpoints"""
import pytest
from httpx import AsyncClient
from unittest.mock import patch


@pytest.mark.asyncio
async def test_get_email_settings_unauthorized(client: AsyncClient):
    """Test getting email settings without auth"""
    response = await client.get("/api/v1/settings/email")
    assert response.status_code in [401, 403]


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
    assert "provider" in data
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
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
@patch("app.services.email_service.resend.Emails.send")
async def test_send_test_email_success(
    mock_send,
    client: AsyncClient,
    admin_headers: dict
):
    """Test sending test email successfully"""
    mock_send.return_value = {"id": "test-id"}

    # Temporarily mark as configured
    from app.services.email_service import email_service
    orig = email_service._configured
    email_service._configured = True

    try:
        response = await client.post(
            "/api/v1/settings/email/test",
            headers=admin_headers,
            json={"email": "recipient@example.com"}
        )

        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert "Test email sent" in data["message"]
    finally:
        email_service._configured = orig


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


@pytest.mark.asyncio
async def test_get_system_settings_seeds_defaults(
    client: AsyncClient,
    auth_headers: dict,
):
    """First read after a fresh DB seeds and returns defaults (3.7 / 4.0 / 180)."""
    response = await client.get("/api/v1/settings/system", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["usd_to_ils"] == 3.7
    assert data["eur_to_ils"] == 4.0
    assert data["min_shelf_life_days"] == 180
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_update_min_shelf_life_days(
    client: AsyncClient,
    auth_headers: dict,
):
    """A manager can update the shelf-life threshold, and it persists -
    this is the single source of truth ReceivingService reads instead of a
    hardcoded constant, so both the value and its persistence matter."""
    response = await client.put(
        "/api/v1/settings/system",
        headers=auth_headers,
        json={"min_shelf_life_days": 90},
    )
    assert response.status_code == 200
    assert response.json()["min_shelf_life_days"] == 90

    # Persisted, not just echoed back
    response = await client.get("/api/v1/settings/system", headers=auth_headers)
    assert response.status_code == 200
    assert response.json()["min_shelf_life_days"] == 90


@pytest.mark.asyncio
async def test_update_min_shelf_life_days_requires_auth(client: AsyncClient):
    """Updating the threshold without auth is rejected."""
    response = await client.put(
        "/api/v1/settings/system",
        json={"min_shelf_life_days": 90},
    )
    assert response.status_code in [401, 403]


@pytest.mark.asyncio
async def test_update_min_shelf_life_days_rejects_negative(
    client: AsyncClient,
    auth_headers: dict,
):
    """Negative day counts are meaningless and rejected at the schema layer."""
    response = await client.put(
        "/api/v1/settings/system",
        headers=auth_headers,
        json={"min_shelf_life_days": -1},
    )
    assert response.status_code == 422


