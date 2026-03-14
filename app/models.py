from sqlalchemy import Column, Integer, String, Numeric, ForeignKey, DateTime
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from database import Base

class Tenant(Base):
    __tablename__ = "tenants"
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())

class Transaction(Base):
    """ACID Strict Entity for Billing"""
    __tablename__ = "transactions"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    amount = Column(Numeric(10, 2), nullable=False)
    status = Column(String, nullable=False) # 'COMPLETED', 'PENDING'
    created_at = Column(DateTime, server_default=func.now())

class ImageJob(Base):
    """Tracks state of image processing job in Primary DB before results are stored in Mongo"""
    __tablename__ = "image_jobs"
    id = Column(Integer, primary_key=True, index=True)
    tenant_id = Column(Integer, ForeignKey("tenants.id"), nullable=False)
    file_path = Column(String, nullable=False)
    status = Column(String, nullable=False) # 'PENDING', 'COMPLETED', 'FAILED'
    created_at = Column(DateTime, server_default=func.now())
