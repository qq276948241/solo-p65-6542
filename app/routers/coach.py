from fastapi import APIRouter, Depends, HTTPException, status, Query
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional

from ..database import get_db
from ..auth import get_current_user, RoleChecker
from ..models import User, UserRole, Coach, Course, Booking, BookingStatus, DayOfWeek, Review
from ..schemas import BookingResponse, CourseResponse, CoachResponse, UserResponse, ReviewResponse, ReviewListResponse
from ..services.review_service import ReviewService

router = APIRouter(prefix="/coach", tags=["Coach"])

coach_checker = RoleChecker([UserRole.COACH])


def get_review_service(db: Session = Depends(get_db)) -> ReviewService:
    return ReviewService(db)


def get_coach_from_user(user: User, db: Session) -> Coach:
    coach = db.query(Coach).filter(Coach.user_id == user.id).first()
    if not coach:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Coach profile not found"
        )
    return coach


@router.get("/bookings/today", response_model=List[BookingResponse])
def get_today_bookings(
    class_date: Optional[date] = Query(None, description="Date to view bookings (default: today)"),
    current_user: User = Depends(coach_checker),
    db: Session = Depends(get_db)
):
    coach = get_coach_from_user(current_user, db)
    if class_date is None:
        class_date = datetime.utcnow().date()

    bookings = db.query(Booking).join(Course).filter(
        Course.coach_id == coach.id,
        Booking.course_date == class_date,
        Booking.status.in_([BookingStatus.BOOKED, BookingStatus.COMPLETED])
    ).order_by(Course.start_time, Booking.booked_at).all()

    return [_build_booking_response(b, db) for b in bookings]


@router.get("/courses", response_model=List[CourseResponse])
def get_my_courses(
    current_user: User = Depends(coach_checker),
    db: Session = Depends(get_db)
):
    coach = get_coach_from_user(current_user, db)
    courses = db.query(Course).filter(
        Course.coach_id == coach.id,
        Course.is_active == True
    ).all()

    return [_build_course_response(c) for c in courses]


@router.get("/profile", response_model=CoachResponse)
def get_profile(
    current_user: User = Depends(coach_checker),
    db: Session = Depends(get_db)
):
    coach = get_coach_from_user(current_user, db)
    user = current_user

    return CoachResponse(
        id=coach.id,
        specialty=coach.specialty,
        bio=coach.bio,
        user=UserResponse(
            id=user.id,
            email=user.email,
            name=user.name,
            phone=user.phone,
            role=user.role,
            created_at=user.created_at
        )
    )


@router.get("/reviews", response_model=ReviewListResponse)
def get_my_reviews(
    course_id: Optional[int] = Query(None, description="Filter reviews by course ID"),
    min_rating: Optional[int] = Query(None, ge=1, le=5, description="Filter by minimum rating"),
    current_user: User = Depends(coach_checker),
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service)
):
    coach = get_coach_from_user(current_user, db)
    reviews, avg_course, avg_coach = review_service.get_coach_reviews(coach, course_id, min_rating)
    return review_service.build_review_list_response(reviews, avg_course, avg_coach)


def _build_course_response(course: Course) -> CourseResponse:
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

    return CourseResponse(
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
        booked_count=0
    )


def _build_booking_response(booking: Booking, db: Session) -> BookingResponse:
    from ..schemas import MemberResponse

    course = booking.course
    course_resp = _build_course_response(course)

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
