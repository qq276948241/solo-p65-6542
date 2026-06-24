# 社区健身工作室课程预约系统 - 架构文档

> 最后更新：2026-06-24
> 项目版本：1.1.0（含评价模块与Service层重构）

---

## 一、系统概览

本系统为社区健身工作室提供完整的课程预约 SaaS 后端，覆盖 **「排课 → 约课 → 签到扣课时 → 课后评价」** 的完整业务闭环。

### 三种角色

| 角色 | 说明 | 典型操作 |
|------|------|----------|
| 👤 **会员** | 购买会员卡的消费者 | 看课表、约课、取消、签到、写评价 |
| 🏋️ **教练** | 授课人员 | 查看当日预约名单、查看收到的评价 |
| 🛠️ **管理员** | 工作室运营人员 | 导出签到CSV、发放会员卡、查看统计数据 |

### 核心业务规则

| 规则 | 说明 |
|------|------|
| **取消预约时限** | 开课前 2 小时内不可取消 |
| **签到扣课时** | 签到成功自动从会员卡扣除 1 次（年卡不扣） |
| **签到时间窗** | 开课前至开课后 30 分钟内可签到 |
| **评价限制** | 同一次预约仅可评价一次，防止刷分 |
| **会员卡类型** | 月卡(10次) / 季卡(30次) / 年卡(无限次) |

---

## 二、技术栈

| 层级 | 技术选型 | 版本说明 |
|------|----------|----------|
| **Web框架** | FastAPI 0.109+ | 基于 Starlette + Pydantic，自动生成 OpenAPI 文档 |
| **ORM** | SQLAlchemy 2.0+ | 声明式模型 + 会话管理 |
| **数据库** | SQLite 3 | 文件型数据库，存储路径 `./fitness.db` |
| **数据校验** | Pydantic 2.5+ | 请求/响应模型自动校验 |
| **鉴权** | JWT (python-jose) | HS256 签名，Token 默认有效期 24 小时 |
| **密码加密** | bcrypt (passlib) | 不可逆哈希存储 |
| **部署** | Uvicorn | ASGI 服务器，支持 `--reload` 热重载 |

---

## 三、目录结构

```
project65/
├── main.py                     # ✅ 应用入口：创建FastAPI实例，注册路由
├── requirements.txt            # ✅ 依赖清单
├── init_db.py                  # ✅ 数据库初始化 + 种子数据脚本
├── fitness.db                  # SQLite数据库文件（运行时自动创建）
│
├── app/
│   ├── __init__.py
│   ├── database.py             # ✅ 数据库引擎 + 会话工厂 + 依赖注入
│   ├── models.py               # ✅ 全部 SQLAlchemy ORM 模型（8张表）
│   ├── schemas.py              # ✅ 全部 Pydantic 请求/响应模型
│   ├── auth.py                 # ✅ JWT认证 + 密码哈希 + 角色权限检查器
│   │
│   ├── routers/                # 📌 API路由层（仅负责参数接收+响应返回）
│   │   ├── __init__.py
│   │   ├── auth.py             # 登录/注册/当前用户
│   │   ├── member.py           # 会员功能：课表/约课/签到/评价
│   │   ├── coach.py            # 教练功能：当日预约/我的评价
│   │   └── admin.py            # 管理员功能：CSV导出/统计/发卡
│   │
│   └── services/               # 📌 业务逻辑层（Service层，从router抽出）
│       ├── __init__.py
│       └── review_service.py   # 评价业务：创建/查询/防重复/异常处理
│
├── test_api.py                 # 端到端API冒烟测试脚本
├── test_duplicate_unit.py      # 评价防重复的单元测试
└── test_duplicate_review.py    # 评价防重复的E2E测试
```

### 架构分层原则

```
┌─────────────────────────────────────────────────────┐
│  routers/ (API层)                                    │
│  职责：参数校验、调用service、返回响应                │
│  不写：复杂业务逻辑、SQL查询                          │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  services/ (业务逻辑层)                              │
│  职责：业务规则校验、事务管理、异常转换、数据组装       │
│  特点：可独立单元测试，不依赖FastAPI                  │
└───────────────────────┬─────────────────────────────┘
                        │
                        ▼
┌─────────────────────────────────────────────────────┐
│  models.py + SQLAlchemy (持久层)                     │
│  职责：数据库CRUD、ORM映射、外键关系                  │
│  不写：业务判断、HTTP异常                              │
└─────────────────────────────────────────────────────┘
```

---

## 四、数据库设计（8张表）

### 4.1 ER关系图

```
                    ┌──────────────┐
                    │    users     │  基础用户表（3种角色共用）
                    │ PK: id       │
                    └──────┬───────┘
                           │ 1:1
            ┌──────────────┼──────────────┐
            │              │              │
    ┌───────▼──────┐  ┌───▼──────┐  ┌───▼───────┐
    │   coaches    │  │ members  │  │  (admin)  │
    │ PK: id       │  │ PK: id   │  │ 无独立表  │
    │ FK: user_id  │  │ FK:user_id│  │ 用role标  │
    └──────┬───────┘  └────┬─────┘  └───────────┘
           │               │
           │ 1:N           │ 1:N
           │               │
    ┌──────▼───────┐  ┌───▼──────────────┐
    │   courses    │  │ membership_cards  │  会员卡
    │ PK: id       │  │ PK: id            │
    │ FK: coach_id │  │ FK: member_id     │
    └──────┬───────┘  └──────────────────┘
           │ 1:N
           │
    ┌──────▼──────────┐
    │    bookings     │  预约表（核心）
    │ PK: id          │
    │ FK: member_id   │─────────┐
    │ FK: course_id   │         │ 1:1
    └──────┬──────────┘         │
           │ 1:1                │
           │                    │
    ┌──────▼───────┐    ┌───────▼────────┐
    │  check_ins   │    │    reviews     │  评价表
    │ PK: id       │    │ PK: id         │
    │ FK: booking  │    │ FK: booking_id │  ◄── UNIQUE约束
    │ FK: member   │    │ FK: member_id  │
    └──────────────┘    │ FK: course_id  │
                        │ FK: coach_id   │
                        └────────────────┘
```

### 4.2 各表详细说明

#### `users` - 用户基础表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| email | String | UNIQUE, NOT NULL | 登录账号（邮箱） |
| hashed_password | String | NOT NULL | bcrypt哈希后的密码 |
| role | Enum | NOT NULL | `member` / `coach` / `admin` |
| name | String | NOT NULL | 真实姓名 |
| phone | String | - | 联系电话 |
| created_at | DateTime | 默认now | 注册时间 |

#### `members` - 会员扩展表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| user_id | Integer | FK(users.id), UNIQUE | 关联基础用户 |
| date_of_birth | Date | - | 出生日期 |

**关联**：`membership_cards` (1:N), `bookings` (1:N), `check_ins` (1:N), `reviews` (1:N)

#### `coaches` - 教练扩展表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| user_id | Integer | FK(users.id), UNIQUE | 关联基础用户 |
| specialty | String | - | 专长（如：瑜伽/力量训练） |
| bio | String | - | 个人简介 |

**关联**：`courses` (1:N), `reviews` (1:N)

#### `membership_cards` - 会员卡

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| member_id | Integer | FK(members.id) | 所属会员 |
| card_type | Enum | NOT NULL | `monthly`月卡 / `quarterly`季卡 / `annual`年卡 |
| total_classes | Integer | NOT NULL | 总课时数（年卡填任意数，不扣减） |
| remaining_classes | Integer | NOT NULL | 剩余课时数 |
| purchase_date | Date | 默认今天 | 购买日期 |
| expiry_date | Date | NOT NULL | 过期日期 |
| is_active | Boolean | 默认True | 是否启用 |

**模型内置方法**：
- `can_book()` → bool：判断是否可以预约（激活+未过期+有课时）
- `deduct_class()` → bool：扣减1课时（年卡不扣）

#### `courses` - 课程表（周循环）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| name | String | NOT NULL | 课程名称 |
| description | String | - | 课程描述 |
| coach_id | Integer | FK(coaches.id) | 授课教练 |
| day_of_week | Enum | NOT NULL | 周一至周日 |
| start_time | Time | NOT NULL | 上课开始时间 |
| end_time | Time | NOT NULL | 上课结束时间 |
| max_capacity | Integer | 默认10 | 最大容量 |
| location | String | - | 上课地点 |
| is_active | Boolean | 默认True | 是否开放预约 |

**关联**：`bookings` (1:N), `reviews` (1:N)

#### `bookings` - 预约表（核心事务表）

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| member_id | Integer | FK(members.id) | 预约会员 |
| course_id | Integer | FK(courses.id) | 预约课程 |
| course_date | Date | NOT NULL | 上课具体日期 |
| status | Enum | 默认booked | `booked`/`cancelled`/`completed`/`no_show` |
| booked_at | DateTime | 默认now | 预约时间 |
| cancelled_at | DateTime | - | 取消时间 |

**模型内置方法**：
- `can_cancel()` → bool：判断当前是否可取消（开课前>2小时 且 状态为booked）

#### `check_ins` - 签到记录表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| booking_id | Integer | FK(bookings.id) | 关联预约 |
| member_id | Integer | FK(members.id) | 签到会员 |
| checkin_time | DateTime | 默认now | 签到时间 |
| qr_code_scanned | Boolean | 默认True | 是否扫码签到 |

#### `reviews` - 课后评价表

| 字段 | 类型 | 约束 | 说明 |
|------|------|------|------|
| id | Integer | PK | 主键 |
| booking_id | Integer | FK | **UNIQUE** - 一约一评 |
| member_id | Integer | FK | 评价会员 |
| course_id | Integer | FK | 被评价课程 |
| coach_id | Integer | FK | 被评价教练 |
| course_rating | Integer | NOT NULL | 课程评分 1-5星 |
| coach_rating | Integer | NOT NULL | 教练评分 1-5星 |
| comment | String | - | 文字点评（最多500字） |
| created_at | DateTime | 默认now | 评价时间 |

**唯一约束**（数据库层双重保护）：
- `uq_reviews_booking_id` → `booking_id` 单独唯一
- `uq_reviews_member_course_booking` → `(member_id, course_id, booking_id)` 联合唯一

---

## 五、鉴权与权限系统

### 5.1 JWT Token 结构

```
Header:  HS256
Payload: {
  "sub": "member@fitness.com",   # 用户邮箱（唯一标识）
  "role": "member",              # 角色：member/coach/admin
  "exp": 1782358000              # 过期时间（默认24h）
}
```

**获取Token**：
```http
POST /auth/login
Content-Type: application/x-www-form-urlencoded

username=member@fitness.com&password=member123
```

**携带Token**：
```http
GET /member/schedule
Authorization: Bearer <access_token>
```

### 5.2 权限检查器

位于 [auth.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo65/project65/app/auth.py)

```python
class RoleChecker:
    def __init__(self, allowed_roles: List[UserRole]):
        self.allowed_roles = allowed_roles

    def __call__(self, user: User = Depends(get_current_user)):
        if user.role not in self.allowed_roles:
            raise HTTPException(403, "权限不足")
        return user
```

**各路由使用的权限**：

| 路由文件 | 权限检查器 | 允许的角色 |
|----------|-----------|-----------|
| `auth.py` `/me` | `get_current_user` | 全部 |
| `member.py` | `member_checker` | member |
| `coach.py` | `coach_checker` | coach |
| `admin.py` | `admin_checker` | admin |

---

## 六、主要API接口清单

### 6.1 认证模块 `/auth`

| 方法 | 路径 | 说明 | 权限 |
|------|------|------|------|
| POST | `/auth/login` | OAuth2登录，返回JWT | 公开 |
| POST | `/auth/register` | 注册新用户 | 公开 |
| GET | `/auth/me` | 获取当前用户信息 | 已登录 |

### 6.2 会员模块 `/member`

| 方法 | 路径 | 说明 | 核心逻辑 |
|------|------|------|----------|
| GET | `/member/schedule` | 查看课表 | 按日期范围展开周循环课程，返回已预约状态 |
| POST | `/member/bookings` | 预约课程 | 校验：容量/会员卡有效/非重复预约 |
| DELETE | `/member/bookings/{id}` | 取消预约 | **2小时限制**：开课前2h内不可取消 |
| GET | `/member/bookings` | 我的预约列表 | 可按状态筛选 |
| POST | `/member/checkin?booking_id=x` | 扫码签到 | 扣减课时，booking状态置为completed |
| GET | `/member/membership-cards` | 查看我的会员卡 | 返回所有卡的剩余次数/有效期 |
| **POST** | **`/member/reviews`** | **提交课后评价** | **仅已完成预约可评，防重复409** |
| **GET** | **`/member/reviews`** | **查看我的评价** | **含课程/教练平均分** |

### 6.3 教练模块 `/coach`

| 方法 | 路径 | 说明 | 核心逻辑 |
|------|------|------|----------|
| GET | `/coach/bookings/today` | 查看当日预约名单 | 按课程开始时间排序 |
| GET | `/coach/courses` | 我的所有课程 | 列出该教练开设的课程 |
| GET | `/coach/profile` | 查看个人资料 | 专长+简介+基础信息 |
| **GET** | **`/coach/reviews`** | **查看收到的评价** | **可按course_id/min_rating筛选，含平均分** |

### 6.4 管理员模块 `/admin`

| 方法 | 路径 | 说明 | 核心逻辑 |
|------|------|------|----------|
| GET | `/admin/checkins/export/csv` | **导出月度签到CSV** | 按年/月筛选，UTF-8 CSV下载 |
| GET | `/admin/checkins` | 查看签到记录（JSON） | 同上，返回数组便于前端渲染 |
| GET | `/admin/users` | 查看所有用户 | 可按role筛选 |
| POST | `/admin/membership-cards` | 发放会员卡 | 管理员为指定会员创建卡片 |
| GET | `/admin/statistics` | 首页统计数据 | 会员数/教练数/课程数/今日签到数等 |

---

## 七、核心业务流程

### 7.1 会员约课 → 签到 → 评价 完整流程

```
步骤1: 查看课表
    GET /member/schedule?start_date=2026-06-24&end_date=2026-06-30
    ↓ 返回未来7天所有课程及已约状态

步骤2: 预约课程
    POST /member/bookings
    { "course_id": 1, "course_date": "2026-06-25" }
    ↓
    校验：1) 容量未满 2) 会员卡有课时 3) 未重复预约
    ↓
    创建booking记录（status=booked）

步骤3: 到店签到（开课前30min内可签）
    POST /member/checkin?booking_id=5
    ↓
    校验：1) booking状态=booked 2) 时间在签到窗
    ↓
    扣减会员卡remaining_classes -= 1
    创建check_in记录
    booking.status → completed

步骤4: 课后评价（只有已签到的课能评）
    POST /member/reviews
    { "booking_id": 5, "course_rating": 5, "coach_rating": 4, "comment": "..." }
    ↓
    三层防重复检查：
      1. service预查booking_id
      2. service预查member+course+date
      3. 数据库UNIQUE约束兜底
    ↓
    返回 409 Conflict 提示：每节课仅可评价一次
```

### 7.2 教练查看当日工作

```
GET /coach/bookings/today?class_date=2026-06-24
↓
返回当天该教练所有课程的预约名单
按上课时间排序，每条包含会员姓名/电话/预约时间
```

### 7.3 管理员月底导出签到

```
GET /admin/checkins/export/csv?year=2026&month=6
↓
自动查询6月1日~6月30日的所有签到记录
生成为UTF-8 CSV，浏览器自动下载
列：签到ID / 会员姓名 / 邮箱 / 电话 / 课程 / 教练 / 日期 / 时间 / 签到时间
```

---

## 八、Service层设计（评价模块示例）

### 8.1 ReviewService 类

文件位置：[app/services/review_service.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo65/project65/app/services/review_service.py)

**为什么要抽Service层？**
- Router中原来堆了~120行业务逻辑（校验+SQL+响应组装）
- member.py和coach.py中有重复的 `_build_review_response` 函数
- 业务规则修改需要改两处，容易遗漏

**Service层公共方法**：

| 方法 | 入参 | 返回 | 职责 |
|------|------|------|------|
| `create_review()` | ReviewCreate, Member | Review 实体 | 完整创建流程（含3层防重复） |
| `get_member_reviews()` | Member | (list, avg_course, avg_coach) | 会员视角查评价 |
| `get_coach_reviews()` | Coach, course_id?, min_rating? | (list, avg_course, avg_coach) | 教练视角查评价（支持筛选） |
| `build_review_response()` | Review | ReviewResponse | 单条DTO组装（1处定义全局用） |
| `build_review_list_response()` | list, avg1, avg2 | ReviewListResponse | 列表DTO+平均分统计 |

**Service层私有方法（内部工具）**：

| 方法 | 作用 |
|------|------|
| `_validate_booking_for_review()` | 检查：预约存在 + 属于该会员 + 状态为COMPLETED |
| `_ensure_no_existing_review()` | 预检查 + 交叉检查防重复 |
| `_create_review_record()` | 写入DB + commit + refresh |
| `_handle_integrity_error()` | 捕获UNIQUE约束异常 → 转409中文提示 |
| `_calculate_averages()` | 静态方法：计算课程/教练平均分 |

**Router层调用方式（精简为3-5行）**：

```python
@router.post("/reviews", response_model=ReviewResponse)
def create_review(
    review_data: ReviewCreate,
    current_user: User = Depends(member_checker),
    db: Session = Depends(get_db),
    review_service: ReviewService = Depends(get_review_service)
):
    member = get_member_from_user(current_user, db)
    review = review_service.create_review(review_data, member)
    return review_service.build_review_response(review)
```

### 8.2 防重复评价的三层保护（重点）

```
第1层: Service预检查（写入前查DB）
  ├─ 按booking_id查询 → 发现已存在 → 抛409
  └─ 按member_id+course_id+course_date交叉查询 → 防止绕过 → 抛409

第2层: 数据库UNIQUE约束（物理写入时）
  └─ uq_reviews_booking_id → booking_id唯一，并发写入时DB直接拒绝

第3层: IntegrityError捕获（并发竞态兜底）
  └─ 场景：请求A和B几乎同时通过第1层检查
          → A写入成功，B触发UNIQUE异常
          → catch IntegrityError → rollback → 抛409
```

---

## 九、部署与运行

### 9.1 本地开发环境

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 初始化数据库 + 种子数据
python init_db.py
#   → 创建fitness.db
#   → 5名教练 + 20节周课 + 1名测试会员 + 季卡(30次)

# 3. 启动开发服务器（热重载）
python -m uvicorn main:app --reload --port 8000

# 4. 打开交互式API文档
#   http://localhost:8000/docs   (Swagger UI)
#   http://localhost:8000/redoc  (ReDoc)
```

### 9.2 默认测试账号

| 角色 | 邮箱 | 密码 |
|------|------|------|
| 🛠️ 管理员 | `admin@fitness.com` | `admin123` |
| 👤 会员 | `member@fitness.com` | `member123` |
| 🏋️ 王教练 | `wang@fitness.com` | `coach123` |
| 🏋️ 李教练 | `li@fitness.com` | `coach123` |
| 🏋️ 张教练 | `zhang@fitness.com` | `coach123` |
| 🏋️ 陈教练 | `chen@fitness.com` | `coach123` |
| 🏋️ 刘教练 | `liu@fitness.com` | `coach123` |

### 9.3 生产部署注意事项

| 事项 | 说明 |
|------|------|
| **SECRET_KEY** | [auth.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo65/project65/app/auth.py#L12) 中的 `SECRET_KEY` 必须替换为强随机字符串 |
| **数据库** | 生产环境建议替换为 PostgreSQL / MySQL，修改 `database.py` 中连接串 |
| **CORS** | [main.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo65/project65/main.py) 中当前 `allow_origins=["*"]`，生产应限定域名 |
| **Token有效期** | [auth.py](file:///d:/code/ai-prompt/solo-chrome-dev-F12/repos/repo65/project65/app/auth.py#L13) 中 `ACCESS_TOKEN_EXPIRE_MINUTES=1440`（24h），可按需缩短 |
| **HTTPS** | 生产必须启用HTTPS，避免Token明文传输 |

---

## 十、常见问题与扩展建议

### Q: 如何新增一个Service？

> 参考 `review_service.py` 的结构：
> 1. 在 `app/services/` 下创建 `xxx_service.py`
> 2. 定义 `XxxService` 类，`__init__` 接收 `db: Session`
> 3. 公共方法返回数据/抛出 `HTTPException`
> 4. 在对应router中通过 `Depends(get_xxx_service)` 注入
> 5. router内仅保留：获取当前用户 → 调用service方法 → 构建响应

### Q: 如何新增一张数据库表？

> 1. 在 `models.py` 中定义模型类（继承`Base`）
> 2. 在 `schemas.py` 中定义 Create/Response DTO
> 3. 若有复杂业务，新建对应 `XxxService`
> 4. 在 `init_db.py` 中补充种子数据
> 5. 删除 `fitness.db` 后重新运行 `python init_db.py`

### Q: 评价模块后续可扩展？

- [ ] 管理员审核/删除违规评价
- [ ] 评价点赞/回复功能
- [ ] 评价图片上传（关联OSS/S3）
- [ ] 按评价排名推荐教练

---

*本文档随代码同步维护，如有功能变更请更新对应章节。*
