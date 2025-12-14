"""
Pydantic schemas for doctor verification and search operations
"""
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict, Any

class DoctorVerificationRequest(BaseModel):
    fullName: str = Field(..., min_length=2, max_length=100, description="Doctor's full name")
    specialty: str = Field(..., min_length=2, max_length=50, description="Medical specialty")
    address: Optional[str] = Field(None, max_length=200, description="Practice address")
    phoneNumber: Optional[str] = Field(None, description="Phone number")
    licenseNumber: Optional[str] = Field(None, max_length=50, description="Medical license number")
    insuranceNetworks: Optional[List[str]] = Field(default=None, description="Affiliated insurance networks")
    servicesOffered: Optional[str] = Field(None, max_length=500, description="Services offered")

    @validator('phoneNumber')
    def validate_phone(cls, v):
        if v and not v.replace('-', '').replace('(', '').replace(')', '').replace(' ', '').replace('+', '').isdigit():
            raise ValueError('Invalid phone number format')
        return v

    @validator('fullName')
    def validate_name(cls, v):
        if len(v.strip().split()) < 2:
            raise ValueError('Full name must contain at least first and last name')
        return v.strip()

class DoctorSearchRequest(BaseModel):
    name: str = Field(..., min_length=2, max_length=100, description="Doctor's name to search")
    specialty: Optional[str] = Field(None, max_length=50, description="Medical specialty filter")

class FieldVerification(BaseModel):
    input_field_a: Optional[Any] = None
    scraped_data_field_a: Optional[Any] = None
    scraped_from: Optional[str] = None
    matches: Optional[bool] = None

class VerificationResult(BaseModel):
    verification_id: str
    timestamp: str
    fullName: FieldVerification
    specialty: FieldVerification
    address: FieldVerification
    phoneNumber: FieldVerification
    licenseNumber: FieldVerification
    insuranceNetworks: FieldVerification
    servicesOffered: FieldVerification

class SearchResult(BaseModel):
    search_id: str
    timestamp: str
    query: Dict[str, Any]
    results: List[Dict[str, Any]]
    total_found: int
    sources_used: List[str]

class DoctorReportResponse(BaseModel):
    report_id: str
    verification_id: str
    full_name_input: Optional[str]
    full_name_scraped: Optional[str]
    full_name_scraped_from: Optional[str]
    full_name_matches: Optional[bool]
    specialty_input: Optional[str]
    specialty_scraped: Optional[str]
    specialty_scraped_from: Optional[str]
    specialty_matches: Optional[bool]
    address_input: Optional[str]
    address_scraped: Optional[str]
    address_scraped_from: Optional[str]
    address_matches: Optional[bool]
    phone_number_input: Optional[str]
    phone_number_scraped: Optional[str]
    phone_number_scraped_from: Optional[str]
    phone_number_matches: Optional[bool]
    license_number_input: Optional[str]
    license_number_scraped: Optional[str]
    license_number_scraped_from: Optional[str]
    license_number_matches: Optional[bool]
    insurance_networks_input: Optional[List[str]]
    insurance_networks_scraped: Optional[List[str]]
    insurance_networks_scraped_from: Optional[str]
    insurance_networks_matches: Optional[bool]
    services_offered_input: Optional[str]
    services_offered_scraped: Optional[List[str]]
    services_offered_scraped_from: Optional[str]
    services_offered_matches: Optional[bool]
    created_at: str
    updated_at: str

    class Config:
        from_attributes = True

class GetReportsResponse(BaseModel):
    reports: List[DoctorReportResponse]
    total_count: int
    skip: int
    limit: int
    has_next: bool
    has_previous: bool

class VerifyAllProgressItem(BaseModel):
    verification_id: str
    full_name: str
    status: str  # 'success', 'failed', 'skipped'
    message: Optional[str] = None

class VerifyAllResponse(BaseModel):
    total_processed: int
    successful: int
    failed: int
    skipped: int
    results: List[VerifyAllProgressItem]
    timestamp: str
