from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date, timedelta
from typing import List, Optional
from calendar import day_name

from ..database import get_db
from ..auth import get_current_user, RoleChecker
from ..models import User, UserRole, Member, Course, Booking, BookingStatus, MembershipCard, CheckIn, DayOfWeek
from ..schemas import (
    BookingCreate, BookingResponse, ScheduleResponse,
    MembershipCardResponse, CheckInResponse, BookingListResponse
)

router = APIRouter(prefix="/member", tags=["Member"])

member_checker = RoleChecker([UserRole.MEMBER])


def get_member_from_user(user: User, db: Session) -> Member:
    member = db.query(Member).filter(Member.user_id == user.id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member profile not found"
        )
    return member


@router.get("/schedule", response_model=List[ScheduleResponse])
def view_schedule(
    start_date: Optional[date] = Query(None, description="Start date (default: today)"),
    end_date: Optional[date] = Query(None, description="End date (default: 7 days from start)"),
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    if start_date is None:
        start_date = datetime.utcnow().date()
    if end_date is None:
        end_date = start_date + timedelta(days=7)

    member = get_member_from_user(current_user, db)
    day_map = {
        0: DayOfWeek.MONDAY, 1: DayOfWeek.TUESDAY, 2: DayOfWeek.WEDNESDAY,
        3: DayOfWeek.THURSDAY, 4: DayOfWeek.FRIDAY, 5: DayOfWeek.SATURDAY, 6: DayOfWeek.SUNDAY
    }

    schedule = []
    current_date = start_date
    while current_date <= end_date:
        day_of_week = day_map[current_date.weekday()]
        courses = db.query(Course).filter(
            Course.day_of_week == day_of_week,
            Course.is_active == True
        ).all()

        for course in courses:
            booked_count = db.query(Booking).filter(
                Booking.course_id == course.id,
                Booking.course_date == current_date,
                Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
            ).count()

            member_booking = db.query(Booking).filter(
                Booking.course_id == course.id,
                Booking.course_date == current_date,
                Booking.member_id == member.id,
                Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
            ).first()

            from ..schemas import CourseResponse, CoachResponse, UserResponse
            coach_user = course.coach.user
            coach_resp = CoachResponse(
                id=course.coach.id,
                specialty=course.coach.specialty,
                bio=course.coach.bio,
                user=UserResponse(
                    id=coach_user.id,
                    email=coach_user.email,
                    name=coach_user.name,
                    phone=coach_user.phone,
                    role=coach_user.role,
                    created_at=coach_user.created_at
                )
            )

            course_resp = CourseResponse(
                id=course.id,
                name=course.name,
                description=course.description,
                day_of_week=course.day_of_week,
                start_time=course.start_time,
                end_time=course.end_time,
                max_capacity=course.max_capacity,
                location=course.location,
                coach_id=course.coach_id,
                coach=coach_resp,
                is_active=course.is_active,
                created_at=course.created_at,
                booked_count=booked_count
            )

            schedule.append(ScheduleResponse(
                course=course_resp,
                date=current_date,
                booked_count=booked_count,
                available_spots=max(0, course.max_capacity - booked_count),
                is_booked_by_member=member_booking is not None
            ))

        current_date += timedelta(days=1)

    return schedule


@router.post("/bookings", response_model=BookingResponse)
def book_course(
    booking_data: BookingCreate,
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    member = get_member_from_user(current_user, db)

    course = db.query(Course).filter(
        Course.id == booking_data.course_id,
        Course.is_active == True
    ).first()
    if not course:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Course not found"
        )

    if booking_data.course_date < datetime.utcnow().date():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot book past courses"
        )

    day_map = {
        0: DayOfWeek.MONDAY, 1: DayOfWeek.TUESDAY, 2: DayOfWeek.WEDNESDAY,
        3: DayOfWeek.THURSDAY, 4: DayOfWeek.FRIDAY, 5: DayOfWeek.SATURDAY, 6: DayOfWeek.SUNDAY
    }
    if day_map[booking_data.course_date.weekday()] != course.day_of_week:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Course is not offered on {day_name[booking_data.course_date.weekday()]}"
        )

    existing_booking = db.query(Booking).filter(
        Booking.member_id == member.id,
        Booking.course_id == booking_data.course_id,
        Booking.course_date == booking_data.course_date,
        Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
    ).first()
    if existing_booking:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="You have already booked this course"
        )

    booked_count = db.query(Booking).filter(
        Booking.course_id == booking_data.course_id,
        Booking.course_date == booking_data.course_date,
        Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
    ).count()
    if booked_count >= course.max_capacity:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Course is fully booked"
        )

    active_card = db.query(MembershipCard).filter(
        MembershipCard.member_id == member.id,
        MembershipCard.is_active == True
    ).first()
    if not active_card or not active_card.can_book():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="No active membership card with available classes"
        )

    new_booking = Booking(
        member_id=member.id,
        course_id=booking_data.course_id,
        course_date=booking_data.course_date,
        status=BookingStatus.BOOKED
    )
    db.add(new_booking)
    db.commit()
    db.refresh(new_booking)

    return _build_booking_response(new_booking, db)


@router.delete("/bookings/{booking_id}", response_model=BookingResponse)
def cancel_booking(
    booking_id: int,
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    member = get_member_from_user(current_user, db)

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.member_id == member.id
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    if not booking.can_cancel():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot cancel booking within 2 hours of class start"
        )

    booking.status = BookingStatus.CANCELLED
    booking.cancelled_at = datetime.utcnow()
    db.commit()
    db.refresh(booking)

    return _build_booking_response(booking, db)


@router.get("/bookings", response_model=BookingListResponse)
def get_my_bookings(
    status: Optional[BookingStatus] = Query(None),
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    member = get_member_from_user(current_user, db)

    query = db.query(Booking).filter(Booking.member_id == member.id)
    if status:
        query = query.filter(Booking.status == status)

    bookings = query.order_by(Booking.course_date, Booking.booked_at).all()
    booking_responses = [_build_booking_response(b, db) for b in bookings]

    return BookingListResponse(bookings=booking_responses, total=len(bookings))


@router.post("/checkin", response_model=CheckInResponse)
def check_in(
    booking_id: int,
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    member = get_member_from_user(current_user, db)

    booking = db.query(Booking).filter(
        Booking.id == booking_id,
        Booking.member_id == member.id
    ).first()
    if not booking:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Booking not found"
        )

    if booking.status != BookingStatus.BOOKED:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Cannot check in for a {booking.status.value} booking"
        )

    course_datetime = datetime.combine(booking.course_date, booking.course.start_time)
    if datetime.utcnow() > course_datetime + timedelta(minutes=30):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Check-in is only available up to 30 minutes after class start"
        )

    existing_checkin = db.query(CheckIn).filter(CheckIn.booking_id == booking_id).first()
    if existing_checkin:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Already checked in for this booking"
        )

    active_card = db.query(MembershipCard).filter(
        MembershipCard.member_id == member.id,
        MembershipCard.is_active == True
    ).first()
    if not active_card or not active_card.deduct_class():
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Failed to deduct class from membership card"
        )

    check_in = CheckIn(
        booking_id=booking.id,
        member_id=member.id,
        qr_code_scanned=True
    )
    db.add(check_in)

    booking.status = BookingStatus.COMPLETED
    db.commit()
    db.refresh(check_in)

    return check_in


@router.get("/membership-cards", response_model=List[MembershipCardResponse])
def get_membership_cards(
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db)
):
    member = get_member_from_user(current_user, db)
    cards = db.query(MembershipCard).filter(MembershipCard.member_id == member.id).all()
    return cards


def _build_booking_response(booking: Booking, db: Session) -> BookingResponse:
    from ..schemas import CourseResponse, CoachResponse, UserResponse, MemberResponse

    course = booking.course
    coach_user = course.coach.user
    coach_resp = CoachResponse(
        id=course.coach.id,
        specialty=course.coach.specialty,
        bio=course.coach.bio,
        user=UserResponse(
            id=coach_user.id,
            email=coach_user.email,
            name=coach_user.name,
            phone=coach_user.phone,
            role=coach_user.role,
            created_at=coach_user.created_at
        )
    )

    member_user = booking.member.user
    member_resp = MemberResponse(
        id=booking.member.id,
        date_of_birth=booking.member.date_of_birth,
        user=UserResponse(
            id=member_user.id,
            email=member_user.email,
            name=member_user.name,
            phone=member_user.phone,
            role=member_user.role,
            created_at=member_user.created_at
        )
    )

    booked_count = db.query(Booking).filter(
        Booking.course_id == course.id,
        Booking.course_date == booking.course_date,
        Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
    ).count()

    course_resp = CourseResponse(
        id=course.id,
        name=course.name,
        description=course.description,
        day_of_week=course.day_of_week,
        start_time=course.start_time,
        end_time=course.end_time,
        max_capacity=course.max_capacity,
        location=course.location,
        coach_id=course.coach_id,
        coach=coach_resp,
        is_active=course.is_active,
        created_at=course.created_at,
        booked_count=booked_count
    )

    return BookingResponse(
        id=booking.id,
        course_id=booking.course_id,
        course_date=booking.course_date,
        member_id=booking.member_id,
        status=booking.status,
        booked_at=booking.booked_at,
        cancelled_at=booking.cancelled_at,
        course=course_resp,
        member=member_resp,
        can_cancel=booking.can_cancel()
    )
