"""Tests for authentication endpoints"""
import pytest
from httpx import AsyncClient

from app.models.user import User


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient, admin_headers: dict):
    """Test user registration by an admin"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "newuser",
            "email": "newuser@example.com",
            "full_name": "New User",
            "password": "securepassword123",
            "role": "viewer",
        },
        headers=admin_headers,
    )
    assert response.status_code == 201
    data = response.json()
    assert data["username"] == "newuser"
    assert data["email"] == "newuser@example.com"
    assert data["role"] == "viewer"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_duplicate_username(client: AsyncClient, test_user: User, admin_headers: dict):
    """Test registration with duplicate username fails"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "testuser",  # Same as test_user
            "email": "different@example.com",
            "full_name": "Another User",
            "password": "securepassword123",
        },
        headers=admin_headers,
    )
    assert response.status_code == 400
    assert "כבר קיים" in response.json()["detail"]


@pytest.mark.asyncio
async def test_register_requires_admin(client: AsyncClient):
    """Test registration without authentication fails"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "sneakyuser",
            "email": "sneaky@example.com",
            "full_name": "Sneaky User",
            "password": "securepassword123",
            "role": "admin",
        },
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_register_requires_admin_role(client: AsyncClient, auth_headers: dict):
    """Test registration by a non-admin (manager) fails"""
    response = await client.post(
        "/api/v1/auth/register",
        json={
            "username": "sneakyuser2",
            "email": "sneaky2@example.com",
            "full_name": "Sneaky User 2",
            "password": "securepassword123",
            "role": "admin",
        },
        headers=auth_headers,
    )
    assert response.status_code == 403


@pytest.mark.asyncio
async def test_login_success(client: AsyncClient, test_user: User):
    """Test successful login"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123",
        },
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data
    assert data["token_type"] == "bearer"


@pytest.mark.asyncio
async def test_login_wrong_password(client: AsyncClient, test_user: User):
    """Test login with wrong password fails"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "wrongpassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_login_locks_account_after_max_failed_attempts(
    client: AsyncClient, test_user: User
):
    """After LOGIN_MAX_FAILED_ATTEMPTS consecutive wrong-password attempts,
    the account locks and even the CORRECT password is rejected with 429
    until the lockout window (checked separately) would expire."""
    from app.api.v1.endpoints.auth import LOGIN_MAX_FAILED_ATTEMPTS

    for _ in range(LOGIN_MAX_FAILED_ATTEMPTS):
        response = await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )
        assert response.status_code == 401

    # Account is now locked - even the correct password is rejected.
    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    assert response.status_code == 429


@pytest.mark.asyncio
async def test_login_success_resets_failed_attempts(
    client: AsyncClient, test_user: User, db_session
):
    """A successful login clears any accumulated failed_login_attempts so
    an occasional typo doesn't slowly march an account toward lockout."""
    for _ in range(3):
        await client.post(
            "/api/v1/auth/login",
            json={"username": "testuser", "password": "wrongpassword"},
        )

    response = await client.post(
        "/api/v1/auth/login",
        json={"username": "testuser", "password": "testpassword123"},
    )
    assert response.status_code == 200

    await db_session.refresh(test_user)
    assert test_user.failed_login_attempts == 0
    assert test_user.locked_until is None


@pytest.mark.asyncio
async def test_login_nonexistent_user(client: AsyncClient):
    """Test login with non-existent user fails"""
    response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "nonexistent",
            "password": "anypassword",
        },
    )
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user(client: AsyncClient, test_user: User, auth_headers: dict):
    """Test getting current user info"""
    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"
    assert data["email"] == "test@example.com"


@pytest.mark.asyncio
async def test_stale_token_for_deleted_user_returns_401(
    client: AsyncClient, test_user: User, auth_headers: dict, db_session
):
    """A structurally valid, unexpired token whose user was deleted after
    issuance is an authentication failure (401), not a 404 - the previous
    404 could make frontend error handling treat this as a missing
    resource instead of prompting re-login."""
    await db_session.delete(test_user)
    await db_session.commit()

    response = await client.get("/api/v1/auth/me", headers=auth_headers)
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_get_current_user_unauthorized(client: AsyncClient):
    """Test getting current user without auth fails"""
    response = await client.get("/api/v1/auth/me")
    assert response.status_code == 403  # No authorization header


@pytest.mark.asyncio
async def test_refresh_token(client: AsyncClient, test_user: User):
    """Test token refresh"""
    # First login to get refresh token
    login_response = await client.post(
        "/api/v1/auth/login",
        json={
            "username": "testuser",
            "password": "testpassword123",
        },
    )
    refresh_token = login_response.json()["refresh_token"]
    
    # Use refresh token
    response = await client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": refresh_token},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert "refresh_token" in data


