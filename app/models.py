from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Date, Time, Enum, Float
from sqlalchemy.orm import relationship
from datetime import datetime, timedelta
import enum

from .database import Base


class UserRole(str, enum.Enum):
    MEMBER = "member"
    COACH = "coach"
    ADMIN = "admin"


class MembershipType(str, enum.Enum):
    MONTHLY = "monthly"
    QUARTERLY = "quarterly"
    ANNUAL = "annual"


class BookingStatus(str, enum.Enum):
    BOOKED = "booked"
    CANCELLED = "cancelled"
    COMPLETED = "completed"
    NO_SHOW = "no_show"


class DayOfWeek(str, enum.Enum):
    MONDAY = "monday"
    TUESDAY = "tuesday"
    WEDNESDAY = "wednesday"
    THURSDAY = "thursday"
    FRIDAY = "friday"
    SATURDAY = "saturday"
    SUNDAY = "sunday"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    email = Column(String, unique=True, index=True, nullable=False)
    hashed_password = Column(String, nullable=False)
    role = Column(Enum(UserRole), nullable=False, default=UserRole.MEMBER)
    name = Column(String, nullable=False)
    phone = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach", back_populates="user", uselist=False)
    member = relationship("Member", back_populates="user", uselist=False)


class Coach(Base):
    __tablename__ = "coaches"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    specialty = Column(String)
    bio = Column(String)

    user = relationship("User", back_populates="coach")
    courses = relationship("Course", back_populates="coach")


class Member(Base):
    __tablename__ = "members"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    date_of_birth = Column(Date)

    user = relationship("User", back_populates="member")
    membership_cards = relationship("MembershipCard", back_populates="member")
    bookings = relationship("Booking", back_populates="member")
    check_ins = relationship("CheckIn", back_populates="member")


class MembershipCard(Base):
    __tablename__ = "membership_cards"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    card_type = Column(Enum(MembershipType), nullable=False)
    total_classes = Column(Integer, nullable=False)
    remaining_classes = Column(Integer, nullable=False)
    purchase_date = Column(Date, default=lambda: datetime.utcnow().date())
    expiry_date = Column(Date, nullable=False)
    is_active = Column(Boolean, default=True)

    member = relationship("Member", back_populates="membership_cards")

    def can_book(self) -> bool:
        if not self.is_active:
            return False
        if datetime.utcnow().date() > self.expiry_date:
            return False
        if self.card_type == MembershipType.ANNUAL:
            return True
        return self.remaining_classes > 0

    def deduct_class(self) -> bool:
        if not self.can_book():
            return False
        if self.card_type != MembershipType.ANNUAL:
            self.remaining_classes -= 1
        return True


class Course(Base):
    __tablename__ = "courses"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String, nullable=False)
    description = Column(String)
    coach_id = Column(Integer, ForeignKey("coaches.id"), nullable=False)
    day_of_week = Column(Enum(DayOfWeek), nullable=False)
    start_time = Column(Time, nullable=False)
    end_time = Column(Time, nullable=False)
    max_capacity = Column(Integer, default=10)
    location = Column(String)
    is_active = Column(Boolean, default=True)
    created_at = Column(DateTime, default=datetime.utcnow)

    coach = relationship("Coach", back_populates="courses")
    bookings = relationship("Booking", back_populates="course")


class Booking(Base):
    __tablename__ = "bookings"

    id = Column(Integer, primary_key=True, index=True)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    course_id = Column(Integer, ForeignKey("courses.id"), nullable=False)
    course_date = Column(Date, nullable=False)
    status = Column(Enum(BookingStatus), default=BookingStatus.BOOKED)
    booked_at = Column(DateTime, default=datetime.utcnow)
    cancelled_at = Column(DateTime)

    member = relationship("Member", back_populates="bookings")
    course = relationship("Course", back_populates="bookings")
    check_in = relationship("CheckIn", back_populates="booking", uselist=False)

    def can_cancel(self) -> bool:
        if self.status != BookingStatus.BOOKED:
            return False
        course_datetime = datetime.combine(self.course_date, self.course.start_time)
        return datetime.utcnow() < (course_datetime - timedelta(hours=2))


class CheckIn(Base):
    __tablename__ = "check_ins"

    id = Column(Integer, primary_key=True, index=True)
    booking_id = Column(Integer, ForeignKey("bookings.id"), nullable=False)
    member_id = Column(Integer, ForeignKey("members.id"), nullable=False)
    checkin_time = Column(DateTime, default=datetime.utcnow)
    qr_code_scanned = Column(Boolean, default=True)

    booking = relationship("Booking", back_populates="check_in")
    member = relationship("Member", back_populates="check_ins")
