from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import date, datetime
from enum import Enum

# Custom Enums matching PostgreSQL schema
class UserRole(str, Enum):
    Admin = "Admin"
    Staff = "Staff"
    Donor = "Donor"
    Hospital = "Hospital"

class StaffStatus(str, Enum):
    Active = "Active"
    OnLeave = "OnLeave"
    Inactive = "Inactive"

class AppointmentStatus(str, Enum):
    Scheduled = "Scheduled"
    Completed = "Completed"
    Cancelled = "Cancelled"
    NoShow = "NoShow"

class RequestStatus(str, Enum):
    Pending = "Pending"
    Approved = "Approved"
    Rejected = "Rejected"
    Fulfilled = "Fulfilled"

class DonationStatus(str, Enum):
    Pending = "Pending"
    Processed = "Processed"
    Discarded = "Discarded"

class TestOutcome(str, Enum):
    Passed = "Passed"
    Failed = "Failed"

# ----------------------------------------------------------------------------
# PYDANTIC SCHEMAS FOR VALIDATION AND RESPONSE
# ----------------------------------------------------------------------------

# 1. User schemas
class UserBase(BaseModel):
    username: str
    enabled: Optional[bool] = True
    role: UserRole = UserRole.Donor

class UserCreate(UserBase):
    password: str

class UserResponse(UserBase):
    id: int
    created_at: datetime

    class Config:
        from_attributes = True

# 2. Blood Type schemas
class BloodTypeResponse(BaseModel):
    id: int
    blood_group: str

    class Config:
        from_attributes = True

# 3. Donor Category schemas
class DonorCategoryBase(BaseModel):
    category_name: str
    description: Optional[str] = None

class DonorCategoryResponse(DonorCategoryBase):
    id: int

    class Config:
        from_attributes = True

# 4. Donor schemas
class DonorBase(BaseModel):
    firstname: str
    lastname: str
    customer_phone: str
    eligibility_state: Optional[bool] = True
    last_donation_date: Optional[date] = None
    address: Optional[str] = None
    blood_type_id: int
    donor_category_id: Optional[int] = None

class DonorCreate(DonorBase):
    user_id: Optional[int] = None

class DonorResponse(DonorBase):
    id: int
    user_id: Optional[int]

    class Config:
        from_attributes = True

# Join Response for Viva Exam explanation
class DonorDetailsResponse(BaseModel):
    id: int
    firstname: str
    lastname: str
    blood_group: str
    category_name: Optional[str]
    last_donation_date: Optional[date]
    customer_phone: str

    class Config:
        from_attributes = True

# 5. Staff schemas
class StaffBase(BaseModel):
    firstname: str
    lastname: str
    status: StaffStatus = StaffStatus.Active
    blood_type_id: int

class StaffCreate(StaffBase):
    user_id: Optional[int] = None

class StaffResponse(StaffBase):
    id: int
    user_id: Optional[int]

    class Config:
        from_attributes = True

# 6. Blood Stock schemas
class BloodStockBase(BaseModel):
    blood_type_id: int
    units_available: int
    received_date: Optional[date] = None
    expiry_date: date

class BloodStockResponse(BloodStockBase):
    id: int

    class Config:
        from_attributes = True

# 7. Blood Request schemas
class BloodRequestBase(BaseModel):
    blood_type_id: int
    units_requested: int
    requester_id: int
    status: RequestStatus = RequestStatus.Pending

class BloodRequestResponse(BloodRequestBase):
    id: int

    class Config:
        from_attributes = True

# 8. Appointment schemas
class AppointmentBase(BaseModel):
    donor_id: int
    staff_id: Optional[int] = None
    appointment_date: datetime
    status: AppointmentStatus = AppointmentStatus.Scheduled

class AppointmentResponse(AppointmentBase):
    id: int

    class Config:
        from_attributes = True
