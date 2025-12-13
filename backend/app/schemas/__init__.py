"""Pydantic schemas for API validation"""
from app.schemas.user import (
    UserCreate,
    UserUpdate,
    UserResponse,
    UserLogin,
    Token,
    TokenRefresh,
)
from app.schemas.item import ItemCreate, ItemUpdate, ItemResponse
from app.schemas.batch import BatchCreate, BatchUpdate, BatchResponse
from app.schemas.location import LocationCreate, LocationUpdate, LocationResponse
from app.schemas.movement import MovementCreate, MovementResponse
from app.schemas.customer import CustomerCreate, CustomerUpdate, CustomerResponse
from app.schemas.delivery_note import (
    DeliveryNoteCreate,
    DeliveryNoteUpdate,
    DeliveryNoteResponse,
    DeliveryNoteItemCreate,
)
from app.schemas.alert import AlertResponse, AlertUpdate
from app.schemas.common import PaginatedResponse, MessageResponse

__all__ = [
    # User
    "UserCreate",
    "UserUpdate",
    "UserResponse",
    "UserLogin",
    "Token",
    "TokenRefresh",
    # Item
    "ItemCreate",
    "ItemUpdate",
    "ItemResponse",
    # Batch
    "BatchCreate",
    "BatchUpdate",
    "BatchResponse",
    # Location
    "LocationCreate",
    "LocationUpdate",
    "LocationResponse",
    # Movement
    "MovementCreate",
    "MovementResponse",
    # Customer
    "CustomerCreate",
    "CustomerUpdate",
    "CustomerResponse",
    # Delivery Note
    "DeliveryNoteCreate",
    "DeliveryNoteUpdate",
    "DeliveryNoteResponse",
    "DeliveryNoteItemCreate",
    # Alert
    "AlertResponse",
    "AlertUpdate",
    # Common
    "PaginatedResponse",
    "MessageResponse",
]


