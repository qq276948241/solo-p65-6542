from sqlalchemy.orm import Session
from fastapi import HTTPException, status
from typing import Optional, Tuple, List

from ..models import Review, Booking, BookingStatus, Member, Coach
from ..schemas import ReviewCreate, ReviewResponse, ReviewListResponse


class ReviewService:
    def __init__(self, db: Session):
        self.db = db

    def create_review(self, review_data: ReviewCreate, member: Member) -> Review:
        booking = self._validate_booking_for_review(review_data.booking_id, member.id)
        self._ensure_no_existing_review(review_data.booking_id)
        return self._create_review_record(review_data, booking, member.id)

    def get_member_reviews(self, member: Member) -> Tuple[List[Review], Optional[float], Optional[float]]:
        reviews = self.db.query(Review).filter(
            Review.member_id == member.id
        ).order_by(Review.created_at.desc()).all()
        avg_course, avg_coach = self._calculate_averages(reviews)
        return reviews, avg_course, avg_coach

    def get_coach_reviews(
        self,
        coach: Coach,
        course_id: Optional[int] = None,
        min_rating: Optional[int] = None
    ) -> Tuple[List[Review], Optional[float], Optional[float]]:
        query = self.db.query(Review).filter(Review.coach_id == coach.id)
        if course_id:
            query = query.filter(Review.course_id == course_id)
        if min_rating:
            query = query.filter(Review.coach_rating >= min_rating)

        reviews = query.order_by(Review.created_at.desc()).all()
        avg_course, avg_coach = self._calculate_averages(reviews)
        return reviews, avg_course, avg_coach

    def build_review_response(self, review: Review) -> ReviewResponse:
        return ReviewResponse(
            id=review.id,
            booking_id=review.booking_id,
            member_id=review.member_id,
            course_id=review.course_id,
            coach_id=review.coach_id,
            course_rating=review.course_rating,
            coach_rating=review.coach_rating,
            comment=review.comment,
            member_name=review.member.user.name,
            course_name=review.course.name,
            coach_name=review.coach.user.name,
            created_at=review.created_at
        )

    def build_review_list_response(
        self,
        reviews: List[Review],
        avg_course: Optional[float],
        avg_coach: Optional[float]
    ) -> ReviewListResponse:
        review_responses = [self.build_review_response(r) for r in reviews]
        return ReviewListResponse(
            reviews=review_responses,
            total=len(reviews),
            average_course_rating=round(avg_course, 2) if avg_course else None,
            average_coach_rating=round(avg_coach, 2) if avg_coach else None
        )

    def _validate_booking_for_review(self, booking_id: int, member_id: int) -> Booking:
        booking = self.db.query(Booking).filter(
            Booking.id == booking_id,
            Booking.member_id == member_id
        ).first()
        if not booking:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Booking not found"
            )
        if booking.status != BookingStatus.COMPLETED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Can only review completed bookings"
            )
        return booking

    def _ensure_no_existing_review(self, booking_id: int) -> None:
        existing_review = self.db.query(Review).filter(
            Review.booking_id == booking_id
        ).first()
        if existing_review:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You have already reviewed this booking"
            )

    def _create_review_record(self, review_data: ReviewCreate, booking: Booking, member_id: int) -> Review:
        new_review = Review(
            booking_id=review_data.booking_id,
            member_id=member_id,
            course_id=booking.course_id,
            coach_id=booking.course.coach_id,
            course_rating=review_data.course_rating,
            coach_rating=review_data.coach_rating,
            comment=review_data.comment
        )
        self.db.add(new_review)
        self.db.commit()
        self.db.refresh(new_review)
        return new_review

    @staticmethod
    def _calculate_averages(reviews: List[Review]) -> Tuple[Optional[float], Optional[float]]:
        if not reviews:
            return None, None
        avg_course = sum(r.course_rating for r in reviews) / len(reviews)
        avg_coach = sum(r.coach_rating for r in reviews) / len(reviews)
        return avg_course, avg_coach
