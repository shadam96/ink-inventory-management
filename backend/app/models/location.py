"""Storage location model for warehouse management"""
from typing import TYPE_CHECKING, List, Optional

from sqlalchemy import String, Text, Boolean
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel

if TYPE_CHECKING:
    from app.models.batch import Batch


class Location(BaseModel):
    """Warehouse storage location model"""
    
    __tablename__ = "locations"
    
    warehouse: Mapped[str] = mapped_column(
        String(50),
        nullable=False,
        index=True
    )
    shelf: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    position: Mapped[str] = mapped_column(
        String(20),
        nullable=False
    )
    location_code: Mapped[str] = mapped_column(
        String(30),
        unique=True,
        index=True,
        nullable=False
    )
    description: Mapped[Optional[str]] = mapped_column(
        Text,
        nullable=True
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False
    )
    
    # Relationships
    batches: Mapped[List["Batch"]] = relationship(
        "Batch",
        back_populates="location",
        lazy="selectin"
    )
    
    def __repr__(self) -> str:
        return f"<Location {self.location_code}>"
    
    @classmethod
    def generate_location_code(
        cls,
        warehouse: str,
        shelf: str,
        position: str
    ) -> str:
        """Generate location code from components"""
        return f"{warehouse}-{shelf}-{position}"
    
    @property
    def batches_count(self) -> int:
        """Count of batches at this location"""
        return len(self.batches)
    
    @property
    def active_batches_count(self) -> int:
        """Count of active batches at this location"""
        return len([b for b in self.batches if b.status == "active"])


