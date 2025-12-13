"""Tests for security utilities"""
import pytest
from datetime import timedelta
from uuid import uuid4

from app.core.security import (
    create_access_token,
    create_refresh_token,
    decode_token,
    get_password_hash,
    verify_password,
    verify_token,
)


def test_password_hashing():
    """Test password hashing and verification"""
    password = "securepassword123"
    hashed = get_password_hash(password)
    
    assert hashed != password
    assert verify_password(password, hashed)
    assert not verify_password("wrongpassword", hashed)


def test_create_access_token():
    """Test JWT access token creation"""
    user_id = uuid4()
    token = create_access_token(subject=user_id, role="manager")
    
    assert token is not None
    assert isinstance(token, str)
    
    # Decode and verify
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == str(user_id)
    assert payload.type == "access"
    assert payload.role == "manager"


def test_create_refresh_token():
    """Test JWT refresh token creation"""
    user_id = uuid4()
    token = create_refresh_token(subject=user_id)
    
    assert token is not None
    
    payload = decode_token(token)
    assert payload is not None
    assert payload.sub == str(user_id)
    assert payload.type == "refresh"


def test_verify_token_valid():
    """Test token verification with valid token"""
    user_id = uuid4()
    token = create_access_token(subject=user_id, role="admin")
    
    token_data = verify_token(token, token_type="access")
    
    assert token_data is not None
    assert token_data.user_id == user_id
    assert token_data.role == "admin"


def test_verify_token_wrong_type():
    """Test token verification with wrong token type"""
    user_id = uuid4()
    access_token = create_access_token(subject=user_id)
    
    # Try to verify access token as refresh token
    token_data = verify_token(access_token, token_type="refresh")
    
    assert token_data is None


def test_verify_token_invalid():
    """Test token verification with invalid token"""
    token_data = verify_token("invalid.token.here")
    assert token_data is None


def test_verify_token_expired():
    """Test token verification with expired token"""
    user_id = uuid4()
    # Create token that's already expired
    token = create_access_token(
        subject=user_id,
        expires_delta=timedelta(seconds=-1)
    )
    
    token_data = verify_token(token)
    assert token_data is None


