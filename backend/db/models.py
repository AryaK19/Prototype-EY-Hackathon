from sqlalchemy import Column, String, DateTime, Text, Boolean
from sqlalchemy.dialects.postgresql import UUID, TIMESTAMP, JSONB
from sqlalchemy.sql import func
import uuid

from db.session import Base


class DoctorReport(Base):
    __tablename__ = 'doctor_reports'
    
    report_id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    verification_id = Column(String(255), nullable=False, unique=True, index=True)
    
    # Full Name verification fields
    full_name_input = Column(String(255))
    full_name_scraped = Column(String(255))
    full_name_scraped_from = Column(String(500))
    full_name_matches = Column(Boolean)
    
    # Specialty verification fields
    specialty_input = Column(String(255))
    specialty_scraped = Column(String(255))
    specialty_scraped_from = Column(String(500))
    specialty_matches = Column(Boolean)
    
    # Address verification fields
    address_input = Column(Text)
    address_scraped = Column(Text)
    address_scraped_from = Column(String(500))
    address_matches = Column(Boolean)
    
    # Phone Number verification fields
    phone_number_input = Column(String(255))
    phone_number_scraped = Column(String(255))
    phone_number_scraped_from = Column(String(500))
    phone_number_matches = Column(Boolean)
    
    # License Number verification fields
    license_number_input = Column(String(255))
    license_number_scraped = Column(String(255))
    license_number_scraped_from = Column(String(500))
    license_number_matches = Column(Boolean)
    
    # Insurance Networks verification fields
    insurance_networks_input = Column(JSONB)
    insurance_networks_scraped = Column(JSONB)
    insurance_networks_scraped_from = Column(String(500))
    insurance_networks_matches = Column(Boolean)
    
    # Services Offered verification fields
    services_offered_input = Column(JSONB)
    services_offered_scraped = Column(JSONB)
    services_offered_scraped_from = Column(String(500))
    services_offered_matches = Column(Boolean)
    
    created_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now())
    updated_at = Column(TIMESTAMP(timezone=True), nullable=False, server_default=func.now(), onupdate=func.now())

    def __repr__(self):
        return f"<DoctorReport(verification_id='{self.verification_id}', created_at='{self.created_at}')>"