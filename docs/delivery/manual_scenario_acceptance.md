# 手动业务流程验收指南

## 1. 文档定位

本文档用于在真实运行库中手动验收自习室预约系统的核心业务时间线。

自动化 `scenario` 测试验证的是隔离测试库中的流程正确性；本文档验证的是本地真实 PostgreSQL、后端服务和管理端页面是否能够完整展示同一条业务链路。

本指南覆盖：

- 正常履约流程
- 未签到违约与座位释放流程
- 管理端预约记录、违约记录和统计结果核对
- 通知日志核对
- 可选真实 QQ SMTP 邮件验证

## 2. 验收前准备

### 2.1 启动依赖

如果 PostgreSQL 跑在 Docker 中，先确认 Docker Desktop 已启动。

在项目根目录执行：

```powershell
cd C:\Users\67220\Desktop\26_SPM
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1 -StartDockerDb
```

如果数据库容器已经在运行，可以执行：

```powershell
cd C:\Users\67220\Desktop\26_SPM
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1
```

脚本会读取 `.env`，执行 `alembic upgrade head`，然后启动 `uvicorn app.main:app`。

### 2.2 打开管理端

浏览器访问：

```text
http://127.0.0.1:8000/admin/login
```

使用当前演示库中的管理员账号登录。

如果登录后看不到资源管理、预约记录、统计或违约入口，先检查该管理员是否拥有对应后台权限。

### 2.3 选择验收日期

建议选择明天或后天，避免被“预约时间必须在未来”的校验影响。

本文示例使用：

```text
2026-04-28
```

实际操作时可以替换为你的验收日期。

### 2.4 记录验收 ID

手动验收过程中需要记录以下 ID：

```text
ROOM_ID=
SEAT_ID_NORMAL=
SEAT_ID_NOSHOW=
STUDENT_NO=
NORMAL_RESERVATION_ID=
NOSHOW_RESERVATION_ID=
```

建议每轮验收使用唯一前缀，例如：

```text
MANUAL-20260428
```

## 3. 准备验收数据

### 3.1 创建学生账号

在管理端点击：

```text
管理首页 -> 创建用户
```

选择：

```text
学生账号
```

建议填写：

```text
姓名：手动验收学生
学生学号：MANUAL-20260428-STU
初始密码：student-pass
账号状态：创建后立即启用
```

创建成功后，记录学生学号。

### 3.2 可选：补充学生邮箱

如果本轮要验证真实 SMTP 邮件，目标学生必须有 `users.email`。

当前学生创建页不负责填写学生邮箱，因此需要在 PowerShell 中补一次邮箱。

说明：

- `.env` 中的 `SMTP_FROM_EMAIL` 是发件邮箱。
- `users.email` 是收件邮箱。
- 手动验收时，可以临时把学生的 `users.email` 设置为同一个 QQ 邮箱，方便确认邮件是否真实收到。

先在新的 PowerShell 窗口导入 `.env`：

```powershell
cd C:\Users\67220\Desktop\26_SPM
Get-Content .\.env | ForEach-Object {
    $line = $_.Trim()
    if ($line -and -not $line.StartsWith("#") -and $line.Contains("=")) {
        $name, $value = $line -split "=", 2
        Set-Item -Path "Env:$($name.Trim())" -Value $value.Trim()
    }
}
```

然后执行：

```powershell
@'
from sqlalchemy import create_engine, text
import os

student_no = "MANUAL-20260428-STU"
email = os.environ["SMTP_FROM_EMAIL"]

engine = create_engine(os.environ["DATABASE_URL"])
with engine.begin() as conn:
    conn.execute(
        text("UPDATE users SET email = :email WHERE student_no = :student_no"),
        {"email": email, "student_no": student_no},
    )
    row = conn.execute(
        text("SELECT id, student_no, email FROM users WHERE student_no = :student_no"),
        {"student_no": student_no},
    ).one()
    print(dict(row._mapping))
'@ | python -
```

如果只验收业务流程，可以不做本步骤，并临时将通知通道设为 `mock`。

### 3.3 创建自习室

在管理端点击：

```text
管理首页 -> 自习室管理
```

创建一个自习室，建议填写：

```text
名称：MANUAL-20260428-ROOM
位置：手动验收楼 101
所属院系：选择一个有效院系
开放时间：08:00
关闭时间：22:00
状态：启用
```

创建后记录 `ROOM_ID`。

如果页面没有直接显示 ID，可以用下面命令查询：

```powershell
@'
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("SELECT id, name, location FROM study_rooms ORDER BY id DESC LIMIT 10")
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

### 3.4 创建两个座位

在管理端点击：

```text
管理首页 -> 座位管理
```

在刚创建的自习室下创建两个座位：

```text
座位编号：MANUAL-NORMAL-01
座位名称：正常履约座位
状态：启用
```

```text
座位编号：MANUAL-NOSHOW-01
座位名称：未签到违约座位
状态：启用
```

记录两个座位 ID。

如果页面没有直接显示 ID，可以用下面命令查询：

```powershell
@'
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT seats.id, seats.seat_code, seats.seat_label, study_rooms.name AS room_name
            FROM seats
            JOIN study_rooms ON study_rooms.id = seats.room_id
            ORDER BY seats.id DESC
            LIMIT 10
        """)
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

## 4. 学生端登录和资源查询

下面步骤使用学生 API 模拟学生端操作。所有数据都会写入真实 PostgreSQL。

在 PowerShell 中设置基础变量：

```powershell
$base = "http://127.0.0.1:8000"
$studentNo = "MANUAL-20260428-STU"
$studentPassword = "student-pass"
$date = "2026-04-28"
$roomId = <ROOM_ID>
$seatIdNormal = <SEAT_ID_NORMAL>
$seatIdNoShow = <SEAT_ID_NOSHOW>
```

学生登录：

```powershell
$loginBody = @{
    student_no = $studentNo
    password = $studentPassword
} | ConvertTo-Json

$login = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/student/auth/login" `
    -ContentType "application/json" `
    -Body $loginBody

$studentHeaders = @{
    Authorization = "Bearer $($login.access_token)"
}
```

查询自习室：

```powershell
$rooms = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms?page=1&page_size=50" `
    -Headers $studentHeaders

$rooms.items | Format-Table id, name, location
```

查询正常履约座位在 `10:00-12:00` 是否可用：

```powershell
$seats = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms/$roomId/seats?date=$date&start_time=10:00:00&end_time=12:00:00" `
    -Headers $studentHeaders

$seats.items | Format-Table seat_id, seat_code, status
```

验收点：

```text
目标自习室可见。
目标座位状态为 AVAILABLE。
```

## 5. SCN-01 正常履约流程

### 5.1 创建预约

创建 `10:00-12:00` 预约：

```powershell
$normalReservationBody = @{
    seat_id = $seatIdNormal
    start_time = "$date`T10:00:00"
    end_time = "$date`T12:00:00"
} | ConvertTo-Json

$normalReservation = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/student/reservations" `
    -Headers $studentHeaders `
    -ContentType "application/json" `
    -Body $normalReservationBody

$normalReservationId = $normalReservation.data.reservation_id
$normalReservation.data
```

记录：

```text
NORMAL_RESERVATION_ID=$normalReservationId
```

### 5.2 触发预约前提醒

预约前 15 分钟是 `09:45`。

如果你希望本轮不发真实邮件，先在当前 PowerShell 中临时覆盖：

```powershell
$env:NOTIFICATION_DEFAULT_CHANNEL = "mock"
```

如果你希望验证真实 QQ SMTP，保持 `.env` 中：

```text
NOTIFICATION_DEFAULT_CHANNEL=smtp_email
```

同时确保该学生已有可用 `email`。

执行提醒任务：

```powershell
@'
from datetime import datetime

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.notification.tasks.reservation_reminder_task import send_reservation_reminders

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    result = send_reservation_reminders(
        session,
        now=datetime.fromisoformat("2026-04-28T09:45:00"),
    )
    print(result.sent_reservation_ids)
'@ | python -
```

再次执行同一命令。

验收点：

```text
第一次输出包含 NORMAL_RESERVATION_ID。
第二次输出为空列表。
notification_logs 中该预约的 RESERVATION_REMINDER 只有一条。
若使用 smtp_email，目标邮箱收到提醒邮件。
```

查询通知日志：

```powershell
@'
from sqlalchemy import create_engine, text
import os

reservation_id = <NORMAL_RESERVATION_ID>

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT id, reservation_id, notification_type, channel, status, sent_at
            FROM notification_logs
            WHERE reservation_id = :reservation_id
            ORDER BY id
        """),
        {"reservation_id": reservation_id},
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

### 5.3 生成签到码并完成签到

生成当天自习室签到码：

```powershell
@'
from datetime import date, datetime

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.checkin.services.code_service import CodeService

room_id = <ROOM_ID>

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    code = CodeService(session, settings=settings).ensure_daily_code(
        room_id,
        code_date=date.fromisoformat("2026-04-28"),
        now=datetime.fromisoformat("2026-04-28T09:45:00"),
    )
    print(code.code)
'@ | python -
```

记录输出的签到码：

```text
CHECKIN_CODE=
```

使用固定业务时间 `10:05` 完成签到：

```powershell
@'
from datetime import datetime
from sqlalchemy import select

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.checkin.schemas.checkin import StudentCodeCheckinRequest
from app.modules.checkin.services.checkin_service import CheckinService
from app.modules.identity.models.user import User

student_no = "MANUAL-20260428-STU"
reservation_id = <NORMAL_RESERVATION_ID>
checkin_code = "<CHECKIN_CODE>"

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    student = session.scalar(select(User).where(User.student_no == student_no))
    result = CheckinService(session, settings=settings).check_in_by_code(
        student,
        StudentCodeCheckinRequest(reservation_id=reservation_id, code=checkin_code),
        now=datetime.fromisoformat("2026-04-28T10:05:00"),
    )
    print({
        "reservation_id": result.reservation_id,
        "status": result.status,
        "checkin_method": result.checkin_method,
        "checkin_at": result.checkin_at,
    })
'@ | python -
```

验收点：

```text
输出 status 为 CHECKED_IN。
管理端预约记录中该预约状态为 CHECKED_IN。
```

### 5.4 管理端核对正常履约结果

浏览器打开：

```text
http://127.0.0.1:8000/admin/reservations/records
```

筛选：

```text
日期范围：2026-04-28 至 2026-04-28
状态：CHECKED_IN
```

验收点：

```text
能看到 NORMAL_RESERVATION_ID。
状态为 CHECKED_IN。
用户、房间、座位和时间段正确。
```

浏览器打开：

```text
http://127.0.0.1:8000/admin/statistics
```

筛选：

```text
日期范围：2026-04-28 至 2026-04-28
```

验收点：

```text
统计中体现该预约贡献的使用时长。
正常履约流程不应新增违约数。
```

## 6. SCN-02 未签到违约与座位释放流程

### 6.1 创建未签到预约

创建 `14:00-16:00` 预约：

```powershell
$noShowReservationBody = @{
    seat_id = $seatIdNoShow
    start_time = "$date`T14:00:00"
    end_time = "$date`T16:00:00"
} | ConvertTo-Json

$noShowReservation = Invoke-RestMethod `
    -Method Post `
    -Uri "$base/student/reservations" `
    -Headers $studentHeaders `
    -ContentType "application/json" `
    -Body $noShowReservationBody

$noShowReservationId = $noShowReservation.data.reservation_id
$noShowReservation.data
```

记录：

```text
NOSHOW_RESERVATION_ID=$noShowReservationId
```

### 6.2 触发未签到提醒

预约开始后 10 分钟是 `14:10`。

```powershell
@'
from datetime import datetime

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.notification.tasks.no_show_reminder_task import send_no_show_reminders

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    result = send_no_show_reminders(
        session,
        now=datetime.fromisoformat("2026-04-28T14:10:00"),
    )
    print(result.sent_reservation_ids)
'@ | python -
```

再次执行同一命令。

验收点：

```text
第一次输出包含 NOSHOW_RESERVATION_ID。
第二次输出为空列表。
notification_logs 中该预约的 NO_SHOW_REMINDER 只有一条。
```

### 6.3 触发超时自动取消和违约记录

违约阈值默认是 15 分钟。使用 `14:16` 触发，避免边界时间误差。

```powershell
@'
from datetime import datetime

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.checkin.tasks.timeout_release_task import release_expired_reservations

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    result = release_expired_reservations(
        session,
        now=datetime.fromisoformat("2026-04-28T14:16:00"),
    )
    print(result.expired_reservation_ids)
'@ | python -
```

再次执行同一命令。

验收点：

```text
第一次输出包含 NOSHOW_RESERVATION_ID。
第二次输出为空列表。
预约状态变为 EXPIRED。
违约记录只生成一条。
```

可选触发自动取消通知：

```powershell
@'
from datetime import datetime

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.notification.tasks.auto_cancel_notice_task import send_auto_cancel_notifications

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    result = send_auto_cancel_notifications(
        session,
        now=datetime.fromisoformat("2026-04-28T14:16:00"),
    )
    print(result.sent_reservation_ids)
'@ | python -
```

### 6.4 验证座位释放

重新查询该座位在 `14:00-16:00` 是否可用：

```powershell
$releasedSeats = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms/$roomId/seats?date=$date&start_time=14:00:00&end_time=16:00:00" `
    -Headers $studentHeaders

$releasedSeats.items | Format-Table seat_id, seat_code, status
```

验收点：

```text
未签到预约使用的座位重新显示为 AVAILABLE。
```

## 7. 管理端核对未签到结果

### 7.1 预约记录

浏览器打开：

```text
http://127.0.0.1:8000/admin/reservations/records
```

筛选：

```text
日期范围：2026-04-28 至 2026-04-28
状态：EXPIRED
```

验收点：

```text
能看到 NOSHOW_RESERVATION_ID。
状态为 EXPIRED。
```

### 7.2 违约记录

浏览器打开：

```text
http://127.0.0.1:8000/admin/violations
```

筛选：

```text
日期范围：2026-04-28 至 2026-04-28
```

验收点：

```text
能看到该学生对应的未签到违约记录。
同一预约只出现一条违约。
```

### 7.3 使用统计

浏览器打开：

```text
http://127.0.0.1:8000/admin/statistics
```

筛选：

```text
日期范围：2026-04-28 至 2026-04-28
```

验收点：

```text
统计中能看到正常履约预约的使用时长。
统计中能看到未签到流程产生的违约数量。
```

## 8. 快速数据库核对命令

如果页面结果和预期不一致，可以用下面命令核对真实库。

### 8.1 预约

```powershell
@'
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT id, user_id, room_id, seat_id, start_time, end_time, status, created_by
            FROM reservations
            ORDER BY id DESC
            LIMIT 20
        """)
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

### 8.2 通知

```powershell
@'
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT id, reservation_id, notification_type, channel, status, sent_at
            FROM notification_logs
            ORDER BY id DESC
            LIMIT 20
        """)
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

### 8.3 违约

```powershell
@'
from sqlalchemy import create_engine, text
import os

engine = create_engine(os.environ["DATABASE_URL"])
with engine.connect() as conn:
    rows = conn.execute(
        text("""
            SELECT id, reservation_id, user_id, violation_type, occurred_at
            FROM violation_records
            ORDER BY id DESC
            LIMIT 20
        """)
    )
    for row in rows:
        print(dict(row._mapping))
'@ | python -
```

## 9. 最终验收清单

正常履约流程：

- 学生可以登录。
- 学生能看到目标自习室。
- 学生能看到目标座位可用。
- 学生能创建预约。
- 预约前提醒只生成一次。
- 学生能在有效窗口内签到。
- 管理端能查到 `CHECKED_IN` 预约。
- 统计中体现正常使用时长。

未签到违约流程：

- 学生能创建未签到预约。
- 未签到提醒只生成一次。
- 超时任务将预约置为 `EXPIRED`。
- 违约记录只生成一次。
- 座位释放后重新可用。
- 管理端能查到 `EXPIRED` 预约。
- 管理端能查到违约记录。
- 统计中体现违约数量。

通知通道：

- `mock` 模式下通知日志状态为 `SENT`。
- `smtp_email` 模式下目标用户有邮箱时可以收到邮件。
- 重复运行同一提醒任务不会重复生成成功通知。

## 10. 常见问题

如果管理端看不到数据：

```text
先确认你操作的是 PostgreSQL 运行库，而不是自动化测试的 sqlite:///:memory:。
```

如果提醒任务报目标用户缺少邮箱：

```text
当前通知通道是 smtp_email，但目标学生没有 users.email。
可以切换为 mock，或先给学生补 email。
```

如果 PowerShell 调用学生 API 返回 401：

```text
重新执行学生登录步骤，刷新 $studentHeaders。
```

如果创建预约失败：

```text
检查预约时间是否在自习室开放时间内。
检查时间是否整点。
检查该座位同一时间段是否已有 BOOKED 或 CHECKED_IN 预约。
```

如果管理端统计为空：

```text
检查统计页面筛选日期是否覆盖预约日期。
检查正常履约预约是否已经完成签到。
检查未签到流程是否已经执行超时释放任务。
```
