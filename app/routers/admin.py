from fastapi import APIRouter, Depends, HTTPException, status, Query
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from datetime import datetime, date
from typing import List, Optional
import io
import csv

from ..database import get_db
from ..auth import get_current_user, RoleChecker
from ..models import User, UserRole, CheckIn, Booking, Course, Coach, Member
from ..schemas import CheckInRecord, UserResponse, MembershipCardResponse, MembershipCardCreate

router = APIRouter(prefix="/admin", tags=["Admin"])

admin_checker = RoleChecker([UserRole.ADMIN])


@router.get("/checkins/export/csv")
def export_monthly_checkins_csv(
    year: int = Query(..., description="Year for the report"),
    month: int = Query(..., ge=1, le=12, description="Month for the report (1-12)"),
    current_user: User = Depends(admin_checker),
    db: Session = Depends(get_db)
):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    check_ins = db.query(CheckIn).join(Booking).join(Course).join(Coach).join(Member, CheckIn.member_id == Member.id).filter(
        CheckIn.checkin_time >= datetime.combine(start_date, datetime.min.time()),
        CheckIn.checkin_time < datetime.combine(end_date, datetime.min.time())
    ).order_by(CheckIn.checkin_time).all()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow([
        "签到ID", "会员姓名", "会员邮箱", "联系电话",
        "课程名称", "教练姓名", "上课日期", "上课时间",
        "签到时间", "二维码扫描"
    ])

    for ci in check_ins:
        member_user = ci.member.user
        coach_user = ci.booking.course.coach.user
        writer.writerow([
            ci.id,
            member_user.name,
            member_user.email,
            member_user.phone or "",
            ci.booking.course.name,
            coach_user.name,
            ci.booking.course_date.isoformat(),
            ci.booking.course.start_time.strftime("%H:%M"),
            ci.checkin_time.strftime("%Y-%m-%d %H:%M:%S"),
            "是" if ci.qr_code_scanned else "否"
        ])

    output.seek(0)
    filename = f"checkins_{year}_{month:02d}.csv"
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename={filename}"}
    )


@router.get("/checkins", response_model=List[CheckInRecord])
def get_checkin_records(
    year: int = Query(..., description="Year for the report"),
    month: int = Query(..., ge=1, le=12, description="Month for the report (1-12)"),
    current_user: User = Depends(admin_checker),
    db: Session = Depends(get_db)
):
    start_date = date(year, month, 1)
    if month == 12:
        end_date = date(year + 1, 1, 1)
    else:
        end_date = date(year, month + 1, 1)

    check_ins = db.query(CheckIn).join(Booking).join(Course).join(Coach).join(Member, CheckIn.member_id == Member.id).filter(
        CheckIn.checkin_time >= datetime.combine(start_date, datetime.min.time()),
        CheckIn.checkin_time < datetime.combine(end_date, datetime.min.time())
    ).order_by(CheckIn.checkin_time).all()

    records = []
    for ci in check_ins:
        member_user = ci.member.user
        coach_user = ci.booking.course.coach.user
        records.append(CheckInRecord(
            checkin_id=ci.id,
            member_name=member_user.name,
            member_email=member_user.email,
            course_name=ci.booking.course.name,
            coach_name=coach_user.name,
            course_date=ci.booking.course_date,
            course_time=ci.booking.course.start_time,
            checkin_time=ci.checkin_time
        ))

    return records


@router.get("/users", response_model=List[UserResponse])
def get_all_users(
    role: Optional[UserRole] = Query(None, description="Filter by user role"),
    current_user: User = Depends(admin_checker),
    db: Session = Depends(get_db)
):
    query = db.query(User)
    if role:
        query = query.filter(User.role == role)
    return query.order_by(User.created_at.desc()).all()


@router.post("/membership-cards", response_model=MembershipCardResponse)
def create_membership_card(
    card_data: MembershipCardCreate,
    current_user: User = Depends(admin_checker),
    db: Session = Depends(get_db)
):
    from ..models import MembershipCard

    member = db.query(Member).filter(Member.id == card_data.member_id).first()
    if not member:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Member not found"
        )

    new_card = MembershipCard(
        member_id=card_data.member_id,
        card_type=card_data.card_type,
        total_classes=card_data.total_classes,
        remaining_classes=card_data.remaining_classes,
        expiry_date=card_data.expiry_date
    )
    db.add(new_card)
    db.commit()
    db.refresh(new_card)
    return new_card


@router.get("/statistics")
def get_statistics(
    current_user: User = Depends(admin_checker),
    db: Session = Depends(get_db)
):
    total_members = db.query(User).filter(User.role == UserRole.MEMBER).count()
    total_coaches = db.query(User).filter(User.role == UserRole.COACH).count()
    total_courses = db.query(Course).filter(Course.is_active == True).count()
    total_checkins = db.query(CheckIn).count()

    today = datetime.utcnow().date()
    today_checkins = db.query(CheckIn).filter(
        CheckIn.checkin_time >= datetime.combine(today, datetime.min.time()),
        CheckIn.checkin_time < datetime.combine(today, datetime.max.time())
    ).count()

    active_memberships = db.query(CheckIn.member_id).distinct().count()

    return {
        "total_members": total_members,
        "total_coaches": total_coaches,
        "total_courses": total_courses,
        "total_checkins": total_checkins,
        "today_checkins": today_checkins,
        "active_memberships": active_memberships
    }
