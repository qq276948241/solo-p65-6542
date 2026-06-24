from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import engine, Base
from app.routers import auth, member, coach, admin

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="社区健身工作室课程预约系统",
    description="会员预约课程、教练查看预约、管理员导出签到记录",
    version="1.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(member.router)
app.include_router(coach.router)
app.include_router(admin.router)


@app.get("/", tags=["Health"])
def root():
    return {"message": "Fitness Studio Booking API is running", "version": "1.0.0"}


@app.get("/health", tags=["Health"])
def health_check():
    return {"status": "healthy"}
