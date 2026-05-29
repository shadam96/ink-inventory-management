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
    """First read after a fresh DB seeds and returns defaults (3.7 / 4.0)."""
    response = await client.get("/api/v1/settings/system", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["usd_to_ils"] == 3.7
    assert data["eur_to_ils"] == 4.0
    assert "updated_at" in data


@pytest.mark.asyncio
async def test_update_system_settings_requires_elevated_role(
    client: AsyncClient,
    viewer_headers: dict,
):
    """Viewers can read FX rates but not change them."""
    response = await client.put(
        "/api/v1/settings/system",
        headers=viewer_headers,
        json={"usd_to_ils": 4.1, "eur_to_ils": 4.5},
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_update_system_settings_persists(
    client: AsyncClient,
    admin_headers: dict,
):
    """Admin update is reflected on the next GET."""
    new_rates = {"usd_to_ils": 4.25, "eur_to_ils": 4.75}
    put_response = await client.put(
        "/api/v1/settings/system", headers=admin_headers, json=new_rates,
    )
    assert put_response.status_code == 200
    put_body = put_response.json()
    assert put_body["usd_to_ils"] == 4.25
    assert put_body["eur_to_ils"] == 4.75

    get_response = await client.get(
        "/api/v1/settings/system", headers=admin_headers,
    )
    get_body = get_response.json()
    assert get_body["usd_to_ils"] == 4.25
    assert get_body["eur_to_ils"] == 4.75


@pytest.mark.asyncio
async def test_update_system_settings_rejects_non_positive(
    client: AsyncClient,
    admin_headers: dict,
):
    """Pydantic validation prevents zero/negative rates from being saved."""
    response = await client.put(
        "/api/v1/settings/system",
        headers=admin_headers,
        json={"usd_to_ils": 0, "eur_to_ils": 4.0},
    )
    assert response.status_code == 422
