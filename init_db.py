import sys
from datetime import datetime, date, time, timedelta

from app.database import SessionLocal, engine, Base
from app.models import (
    User, UserRole, Coach, Member, Course, MembershipCard,
    MembershipType, DayOfWeek, Booking, BookingStatus, CheckIn, Review
)
from app.auth import get_password_hash

Base.metadata.drop_all(bind=engine)
Base.metadata.create_all(bind=engine)

db = SessionLocal()

try:
    print("Creating admin user...")
    admin = User(
        email="admin@fitness.com",
        hashed_password=get_password_hash("admin123"),
        role=UserRole.ADMIN,
        name="系统管理员",
        phone="13800000000"
    )
    db.add(admin)

    print("Creating coaches...")
    coaches_data = [
        {"name": "王教练", "email": "wang@fitness.com", "password": "coach123",
         "phone": "13800000001", "specialty": "瑜伽/普拉提", "bio": "10年瑜伽教学经验，印度认证教练"},
        {"name": "李教练", "email": "li@fitness.com", "password": "coach123",
         "phone": "13800000002", "specialty": "力量训练/体能", "bio": "前国家队体能教练，专注力量训练"},
        {"name": "张教练", "email": "zhang@fitness.com", "password": "coach123",
         "phone": "13800000003", "specialty": "有氧舞蹈/Zumba", "bio": "Zumba国际认证教练，充满活力"},
        {"name": "陈教练", "email": "chen@fitness.com", "password": "coach123",
         "phone": "13800000004", "specialty": "拳击/搏击", "bio": "专业拳击运动员出身，8年教学经验"},
        {"name": "刘教练", "email": "liu@fitness.com", "password": "coach123",
         "phone": "13800000005", "specialty": "HIIT/燃脂", "bio": "HIIT认证教练，高效减脂专家"},
    ]

    coaches = []
    for coach_data in coaches_data:
        user = User(
            email=coach_data["email"],
            hashed_password=get_password_hash(coach_data["password"]),
            role=UserRole.COACH,
            name=coach_data["name"],
            phone=coach_data["phone"]
        )
        db.add(user)
        db.flush()
        coach = Coach(
            user_id=user.id,
            specialty=coach_data["specialty"],
            bio=coach_data["bio"]
        )
        db.add(coach)
        db.flush()
        coaches.append(coach)

    print("Creating sample member...")
    member_user = User(
        email="member@fitness.com",
        hashed_password=get_password_hash("member123"),
        role=UserRole.MEMBER,
        name="测试会员",
        phone="13900000001"
    )
    db.add(member_user)
    db.flush()
    member = Member(user_id=member_user.id, date_of_birth=date(1990, 1, 15))
    db.add(member)
    db.flush()

    print("Creating membership card for sample member...")
    today = date.today()
    membership = MembershipCard(
        member_id=member.id,
        card_type=MembershipType.QUARTERLY,
        total_classes=30,
        remaining_classes=30,
        purchase_date=today,
        expiry_date=today + timedelta(days=90)
    )
    db.add(membership)

    print("Creating 20 weekly courses...")
    courses_data = [
        # 王教练 - 瑜伽/普拉提 (5节)
        ("晨间瑜伽", "舒缓身心，开启美好一天", 0, time(7, 0), time(8, 0), 15, "A室"),
        ("基础瑜伽", "适合初学者的瑜伽入门课程", 0, time(19, 0), time(20, 0), 15, "A室"),
        ("普拉提核心", "强化核心肌群，改善体态", 2, time(9, 0), time(10, 0), 12, "A室"),
        ("阴瑜伽", "深度拉伸，释放压力", 2, time(19, 0), time(20, 30), 15, "A室"),
        ("流瑜伽", "流畅体式，提升活力", 4, time(18, 0), time(19, 0), 15, "A室"),

        # 李教练 - 力量训练/体能 (5节)
        ("力量塑形", "全身力量训练，塑造完美线条", 1, time(9, 0), time(10, 0), 12, "力量区"),
        ("核心训练", "腹肌马甲线专项训练", 1, time(19, 0), time(19, 45), 15, "力量区"),
        ("体能提升", "综合体能训练，提升运动表现", 3, time(18, 0), time(19, 0), 12, "力量区"),
        ("下肢力量", "臀腿专项训练", 5, time(10, 0), time(11, 0), 12, "力量区"),
        ("上肢力量", "肩背手臂塑形", 6, time(14, 0), time(15, 0), 12, "力量区"),

        # 张教练 - 有氧舞蹈/Zumba (4节)
        ("活力Zumba", "快乐燃脂，舞动人生", 1, time(19, 0), time(20, 0), 20, "舞蹈室"),
        ("有氧舞蹈", "轻松愉悦的有氧运动", 2, time(18, 0), time(19, 0), 20, "舞蹈室"),
        ("爵士舞入门", "零基础爵士舞教学", 4, time(19, 0), time(20, 0), 15, "舞蹈室"),
        ("尊巴进阶", "高强度尊巴燃脂", 6, time(16, 0), time(17, 0), 20, "舞蹈室"),

        # 陈教练 - 拳击/搏击 (3节)
        ("搏击操", "燃脂减压，释放能量", 0, time(19, 0), time(20, 0), 15, "搏击区"),
        ("拳击基础", "系统学习拳击技术", 5, time(19, 0), time(20, 0), 10, "搏击区"),
        ("MMA体能", "综合格斗体能训练", 6, time(19, 0), time(20, 30), 10, "搏击区"),

        # 刘教练 - HIIT/燃脂 (3节)
        ("HIIT燃脂", "高强度间歇训练，快速燃脂", 1, time(18, 0), time(18, 45), 15, "多功能区"),
        ("Tabata挑战", "4分钟极速燃脂", 3, time(19, 0), time(19, 30), 15, "多功能区"),
        ("循环训练", "全身燃脂循环训练", 5, time(18, 0), time(19, 0), 15, "多功能区"),
    ]

    coach_idx = 0
    course_count = 0
    for name, desc, day, start, end, cap, loc in courses_data:
        if course_count < 5:
            coach_idx = 0
        elif course_count < 10:
            coach_idx = 1
        elif course_count < 14:
            coach_idx = 2
        elif course_count < 17:
            coach_idx = 3
        else:
            coach_idx = 4

        day_enum = list(DayOfWeek)[day]
        course = Course(
            name=name,
            description=desc,
            coach_id=coaches[coach_idx].id,
            day_of_week=day_enum,
            start_time=start,
            end_time=end,
            max_capacity=cap,
            location=loc
        )
        db.add(course)
        course_count += 1

    print(f"Created {course_count} courses")

    print("Creating some sample bookings and check-ins...")
    all_courses = db.query(Course).all()
    today = date.today()
    day_map = {
        0: DayOfWeek.MONDAY, 1: DayOfWeek.TUESDAY, 2: DayOfWeek.WEDNESDAY,
        3: DayOfWeek.THURSDAY, 4: DayOfWeek.FRIDAY, 5: DayOfWeek.SATURDAY, 6: DayOfWeek.SUNDAY
    }

    for i in range(-3, 4):
        course_date = today + timedelta(days=i)
        day_enum = day_map[course_date.weekday()]
        day_courses = [c for c in all_courses if c.day_of_week == day_enum]
        for course in day_courses[:2]:
            booking = Booking(
                member_id=member.id,
                course_id=course.id,
                course_date=course_date,
                status=BookingStatus.COMPLETED if i < 0 else BookingStatus.BOOKED
            )
            db.add(booking)
            db.flush()
            if i < 0:
                checkin_time = datetime.combine(course_date, course.start_time) + timedelta(minutes=5)
                checkin = CheckIn(
                    booking_id=booking.id,
                    member_id=member.id,
                    checkin_time=checkin_time,
                    qr_code_scanned=True
                )
                db.add(checkin)
                membership.remaining_classes -= 1

    print("Creating sample reviews...")
    completed_bookings = db.query(Booking).filter(
        Booking.member_id == member.id,
        Booking.status == BookingStatus.COMPLETED
    ).all()

    comments = [
        "教练非常专业，课程安排很合理，强烈推荐！",
        "课程氛围很好，运动量适中，下次还会来。",
        "王教练的指导很细致，动作纠正到位。",
        "设施齐全，体验很棒，已经办了季卡！",
        "强度刚好，出了很多汗，感觉很充实。",
    ]

    review_count = 0
    for i, booking in enumerate(completed_bookings):
        review = Review(
            booking_id=booking.id,
            member_id=member.id,
            course_id=booking.course_id,
            coach_id=booking.course.coach_id,
            course_rating=5 - (i % 2),
            coach_rating=5 - (i % 3),
            comment=comments[i % len(comments)]
        )
        db.add(review)
        review_count += 1

    db.commit()
    print(f"Created {review_count} sample reviews")
    print("\nDatabase initialized successfully!")
    print("\nDefault accounts:")
    print("  Admin:    admin@fitness.com / admin123")
    print("  Member:   member@fitness.com / member123")
    print("  Coaches:")
    for c in coaches_data:
        print(f"    {c['name']}: {c['email']} / coach123")
    print(f"\nCreated {len(coaches)} coaches, {course_count} weekly courses")

except Exception as e:
    db.rollback()
    print(f"Error: {e}")
    sys.exit(1)
finally:
    db.close()
