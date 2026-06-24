from pydantic import BaseModel, EmailStr, Field
from datetime import datetime, date, time
from typing import Optional, List
from .models import UserRole, MembershipType, BookingStatus, DayOfWeek


class Token(BaseModel):
    access_token: str
    token_type: str


class TokenData(BaseModel):
    email: Optional[str] = None


class UserBase(BaseModel):
    email: EmailStr
    name: str
    phone: Optional[str] = None


class UserCreate(UserBase):
    password: str
    role: UserRole = UserRole.MEMBER


class UserResponse(UserBase):
    id: int
    role: UserRole
    created_at: datetime

    class Config:
        from_attributes = True


class CoachBase(BaseModel):
    specialty: Optional[str] = None
    bio: Optional[str] = None


class CoachCreate(CoachBase):
    user_id: int


class CoachResponse(CoachBase):
    id: int
    user: UserResponse

    class Config:
        from_attributes = True


class MemberBase(BaseModel):
    date_of_birth: Optional[date] = None


class MemberCreate(MemberBase):
    user_id: int


class MemberResponse(MemberBase):
    id: int
    user: UserResponse

    class Config:
        from_attributes = True


class MembershipCardBase(BaseModel):
    card_type: MembershipType
    total_classes: int
    remaining_classes: int
    expiry_date: date


class MembershipCardCreate(MembershipCardBase):
    member_id: int


class MembershipCardResponse(MembershipCardBase):
    id: int
    member_id: int
    purchase_date: date
    is_active: bool

    class Config:
        from_attributes = True


class CourseBase(BaseModel):
    name: str
    description: Optional[str] = None
    day_of_week: DayOfWeek
    start_time: time
    end_time: time
    max_capacity: int = 10
    location: Optional[str] = None


class CourseCreate(CourseBase):
    coach_id: int


class CourseResponse(CourseBase):
    id: int
    coach_id: int
    coach: CoachResponse
    is_active: bool
    created_at: datetime
    booked_count: Optional[int] = 0

    class Config:
        from_attributes = True


class BookingBase(BaseModel):
    course_id: int
    course_date: date


class BookingCreate(BookingBase):
    pass


class BookingResponse(BookingBase):
    id: int
    member_id: int
    status: BookingStatus
    booked_at: datetime
    cancelled_at: Optional[datetime]
    course: CourseResponse
    member: MemberResponse
    can_cancel: bool

    class Config:
        from_attributes = True


class CheckInBase(BaseModel):
    booking_id: int


class CheckInCreate(CheckInBase):
    pass


class CheckInResponse(CheckInBase):
    id: int
    member_id: int
    checkin_time: datetime
    qr_code_scanned: bool

    class Config:
        from_attributes = True


class ScheduleResponse(BaseModel):
    course: CourseResponse
    date: date
    booked_count: int
    available_spots: int
    is_booked_by_member: bool = False


class BookingListResponse(BaseModel):
    bookings: List[BookingResponse]
    total: int


class CheckInRecord(BaseModel):
    checkin_id: int
    member_name: str
    member_email: str
    course_name: str
    coach_name: str
    course_date: date
    course_time: time
    checkin_time: datetime

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class CheckInRequest(BaseModel):
    qr_code_data: str


class ReviewBase(BaseModel):
    course_rating: int = Field(..., ge=1, le=5, description="Course rating from 1 to 5 stars")
    coach_rating: int = Field(..., ge=1, le=5, description="Coach rating from 1 to 5 stars")
    comment: Optional[str] = Field(None, max_length=500, description="Optional text comment")


class ReviewCreate(ReviewBase):
    booking_id: int


class ReviewResponse(ReviewBase):
    id: int
    booking_id: int
    member_id: int
    course_id: int
    coach_id: int
    member_name: Optional[str] = None
    course_name: Optional[str] = None
    coach_name: Optional[str] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ReviewListResponse(BaseModel):
    reviews: List[ReviewResponse]
    total: int
    average_course_rating: Optional[float] = None
    average_coach_rating: Optional[float] = None
