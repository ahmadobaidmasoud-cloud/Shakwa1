from sqlalchemy import Column, Integer, Boolean, DateTime, func, ForeignKey
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import relationship
from app.db.session import Base
import uuid


class TicketConfiguration(Base):
    __tablename__ = "ticket_configurations"

    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(UUID(as_uuid=True), ForeignKey("tenants.id", ondelete="CASCADE"), nullable=False, unique=True, index=True)
    first_name = Column(Boolean, default=True, nullable=False)
    last_name = Column(Boolean, default=True, nullable=False)
    email = Column(Boolean, default=True, nullable=False)
    phone = Column(Boolean, default=False, nullable=False)
    details = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at = Column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)

    class Config:
        from_attributes = True
