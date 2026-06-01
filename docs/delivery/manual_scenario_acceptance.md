# 手动业务流程验收指南

## 1. 文档定位

本文档用于在本机真实运行环境中验收自习室预约系统的核心业务流程。

当前阶段的原则是：

- 本地项目是唯一修复源，云端只作为后续部署目标。
- 手动验收优先使用管理端页面按钮完成基础数据准备。
- 需要推进“预约提醒、签到、超时释放”等时间线时，再使用少量脚本。
- 验收结果记录到 `docs/delivery/manual_scenario_acceptance_record.md`。
- 通过项只需要在记录单里勾选；不通过项粘贴截图即可。

本文覆盖：

- 管理端登录、菜单和主题基础可用性
- 院系、用户、自习室、座位基础数据准备
- 学生登录、预约、签到
- 未签到提醒、超时释放、违约记录
- 管理端预约记录、违约记录和统计核对
- 可选 QQ SMTP 真实邮件验证

## 2. 启动本地环境

### 2.1 启动 Docker 和后端

先确认 Docker Desktop 已启动。

在项目根目录执行：

```powershell
cd C:\Users\67220\Desktop\26_SPM
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1 -StartDockerDb
```

如果数据库容器已经运行，可以只启动后端：

```powershell
cd C:\Users\67220\Desktop\26_SPM
powershell -ExecutionPolicy Bypass -File .\scripts\start_backend.ps1
```

### 2.2 确认 PostgreSQL 迁移到最新

如果管理端看不到“院系管理”等新增菜单，不要直接裸跑 `alembic upgrade head`。裸跑时可能升级默认 SQLite，而不是本地 PostgreSQL。

请使用下面命令升级真实本地 PostgreSQL：

```powershell
cd C:\Users\67220\Desktop\26_SPM
$env:DATABASE_URL='postgresql+psycopg://spm:spm@127.0.0.1:5432/spm'
alembic upgrade head
```

升级后重启后端并重新登录管理端。

### 2.3 打开管理端

浏览器访问：

```text
http://127.0.0.1:8000/admin/login
```

当前演示库常用管理员账号：

```text
登录标识：admin
密码：admin
```

登录后应能看到：

- 管理首页
- 院系管理
- 创建用户
- 自习室管理
- 座位管理
- 动态签到码
- 预约记录
- 违约记录
- 通知日志
- 统计查询

如果入口缺失，先执行 2.2 的 PostgreSQL migration，再重启后端、退出并重新登录。

## 3. 本轮命名规则

为避免和历史数据混在一起，每轮验收使用一个唯一前缀。

示例：

```text
PREFIX=MANUAL-20260429-01
```

建议按下面规则填写页面表单：

```text
院系名称：MANUAL-20260429-01-学院
院系编码：MANUAL-20260429-01-DEPT

学生姓名：MANUAL-20260429-01-学生
学生学号：MANUAL-20260429-01-STU
初始密码：student-pass

自习室名称：MANUAL-20260429-01-ROOM
自习室位置：手动验收楼 101

正常履约座位编号：MANUAL-20260429-01-NORMAL
未签到座位编号：MANUAL-20260429-01-NOSHOW
```

预约日期请选择未来日期，避免被“预约时间必须在未来”的校验挡住。示例：

```text
验收日期：2026-05-01
```

## 4. 用管理端按钮准备基础数据

### 4.1 新增院系

入口：

```text
管理首页 -> 院系管理
```

操作：

1. 填写院系名称。
2. 填写院系编码。
3. 保持“启用”。
4. 点击“创建院系”。

通过标准：

- 页面提示创建成功。
- 院系列表出现刚创建的院系。
- 该院系处于启用状态。

### 4.2 创建学生用户

入口：

```text
管理首页 -> 创建用户
```

操作：

1. 选择“学生账号”。
2. 填写学生姓名、学生学号、初始密码。
3. 选择刚创建的院系。
4. 如需验证真实邮件，填写通知邮箱；否则可留空。
5. 保持“创建后立即启用”。
6. 点击“创建用户账号”。

通过标准：

- 页面提示学生账号创建成功。
- 学生账号可用于学生端登录。

### 4.3 创建院系专属自习室

入口：

```text
管理首页 -> 自习室管理
```

操作：

1. 填写自习室名称和位置。
2. 开放范围选择“院系专属”。
3. 所属院系选择刚创建的院系。
4. 开放时间填写 `08:00`。
5. 关闭时间填写 `22:00`。
6. 保持“创建后立即启用”。
7. 点击“创建自习室”。

通过标准：

- 页面提示自习室创建成功。
- 自习室列表显示刚创建的房间。
- 卡片中显示“院系专属”和正确院系。
- 切换“公共开放 / 院系专属”时，当前表单的所属院系下拉框可正常启用和禁用。

### 4.4 创建两个座位

入口：

```text
管理首页 -> 座位管理
```

操作：

1. 所属自习室选择刚创建的自习室。
2. 创建正常履约座位，例如 `MANUAL-20260429-01-NORMAL`。
3. 再创建未签到座位，例如 `MANUAL-20260429-01-NOSHOW`。
4. 两个座位都保持启用。

通过标准：

- 座位列表显示两个座位。
- 两个座位都归属于刚创建的自习室。

## 5. 学生端预约与流程推进

当前项目没有单独的网页学生端，学生端验收可使用微信小程序或 HTTP API。为了稳定复现时间线，推荐本轮使用 PowerShell 调用学生 API 和公开 task/service。

### 5.1 设置基础变量

把下面变量改成本轮实际值：

```powershell
$base = "http://127.0.0.1:8000"
$studentNo = "MANUAL-20260429-01-STU"
$studentPassword = "student-pass"
$date = "2026-05-01"
```

如果你不想手动找 ID，可以用下面命令按本轮前缀查询：

```powershell
$prefix = "MANUAL-20260429-01"
docker compose exec -T db psql -U spm -d spm -c "SELECT id, name, code, is_active FROM departments WHERE code LIKE '$prefix%';"
docker compose exec -T db psql -U spm -d spm -c "SELECT id, name, location, department_id, is_department_only, is_active FROM study_rooms WHERE name LIKE '$prefix%';"
docker compose exec -T db psql -U spm -d spm -c "SELECT id, room_id, seat_code, seat_label, is_active FROM seats WHERE seat_code LIKE '$prefix%' ORDER BY id;"
```

然后补充：

```powershell
$roomId = <刚创建的自习室 ID>
$seatIdNormal = <正常履约座位 ID>
$seatIdNoShow = <未签到座位 ID>
```

### 5.2 学生登录

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

通过标准：

- 返回 `access_token`。

### 5.3 查询资源可见性

查询自习室：

```powershell
$rooms = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms?page=1&page_size=50" `
    -Headers $studentHeaders

$rooms.items | Format-Table id, name, location
```

查询座位：

```powershell
$seats = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms/$roomId/seats?date=$date&start_time=10:00:00&end_time=12:00:00" `
    -Headers $studentHeaders

$seats.items | Format-Table seat_id, seat_code, status
```

通过标准：

- 学生能看到刚创建的院系专属自习室。
- 两个目标座位在对应时间段为 `AVAILABLE`。

### 5.4 SCN-01：正常履约预约

创建 `09:30-10:30` 预约：

```powershell
$normalReservationBody = @{
    seat_id = $seatIdNormal
    start_time = "$date`T09:30:00"
    end_time = "$date`T10:30:00"
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

运行调度器 tick，模拟预约前 15 分钟：

```powershell
$env:ACCEPTANCE_NOW = "$date`T09:15:00"
@'
from datetime import datetime
import os

from app.core.config import load_settings
from app.core.database import configure_database
from app.modules.notification.services.scheduler_service import tick

settings = load_settings()
configure_database(settings.database_url)

result = tick(now=datetime.fromisoformat(os.environ["ACCEPTANCE_NOW"]))
print(result.reservation_reminder_ids)
'@ | python -
```

同一命令再执行一次，第二次应输出空列表。

获取当前动态签到码：

```powershell
$env:ACCEPTANCE_ROOM_ID = "$roomId"
$env:ACCEPTANCE_NOW = "$date`T09:35:00"
@'
from datetime import datetime
import os

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.checkin.services.code_service import CodeService

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    code = CodeService(session, settings=settings).get_current_dynamic_code(
        int(os.environ["ACCEPTANCE_ROOM_ID"]),
        now=datetime.fromisoformat(os.environ["ACCEPTANCE_NOW"]),
    )
    print(code.code)
'@ | python -
```

把输出的当前 5 分钟时间片签到码填入：

```powershell
$checkinCode = "<上一步输出的签到码>"
```

执行签到：

```powershell
$env:ACCEPTANCE_STUDENT_NO = "$studentNo"
$env:ACCEPTANCE_RESERVATION_ID = "$normalReservationId"
$env:ACCEPTANCE_CHECKIN_CODE = "$checkinCode"
$env:ACCEPTANCE_NOW = "$date`T09:35:00"
@'
from datetime import datetime
import os
from sqlalchemy import select

from app.core.config import load_settings
from app.core.database import configure_database, SessionLocal
from app.modules.checkin.schemas.checkin import StudentCodeCheckinRequest
from app.modules.checkin.services.checkin_service import CheckinService
from app.modules.identity.models.user import User

settings = load_settings()
configure_database(settings.database_url)

with SessionLocal() as session:
    student = session.scalar(select(User).where(User.student_no == os.environ["ACCEPTANCE_STUDENT_NO"]))
    result = CheckinService(session, settings=settings).check_in_by_code(
        student,
        StudentCodeCheckinRequest(
            reservation_id=int(os.environ["ACCEPTANCE_RESERVATION_ID"]),
            code=os.environ["ACCEPTANCE_CHECKIN_CODE"],
        ),
        now=datetime.fromisoformat(os.environ["ACCEPTANCE_NOW"]),
    )
    print({"reservation_id": result.reservation_id, "status": result.status})
'@ | python -
```

通过标准：

- 预约创建成功。
- 预约前提醒第一次包含该预约 ID，第二次为空。
- 签到输出 `CHECKED_IN`。

### 5.5 SCN-02：未签到违约与座位释放

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

运行调度器 tick，模拟预约开始后 10 分钟：

```powershell
$env:ACCEPTANCE_NOW = "$date`T14:10:00"
@'
from datetime import datetime
import os

from app.core.config import load_settings
from app.core.database import configure_database
from app.modules.notification.services.scheduler_service import tick

settings = load_settings()
configure_database(settings.database_url)

result = tick(now=datetime.fromisoformat(os.environ["ACCEPTANCE_NOW"]))
print(result.no_show_reminder_ids)
'@ | python -
```

同一命令再执行一次，第二次应输出空列表。

运行调度器 tick，模拟超时释放：

```powershell
$env:ACCEPTANCE_NOW = "$date`T14:16:00"
@'
from datetime import datetime
import os

from app.core.config import load_settings
from app.core.database import configure_database
from app.modules.notification.services.scheduler_service import tick

settings = load_settings()
configure_database(settings.database_url)

result = tick(now=datetime.fromisoformat(os.environ["ACCEPTANCE_NOW"]))
print({
    "expired_reservation_ids": result.expired_reservation_ids,
    "timeout_release_notification_ids": result.timeout_release_notification_ids,
})
'@ | python -
```

同一命令再执行一次，第二次应输出空列表。

重新查询座位释放：

```powershell
$releasedSeats = Invoke-RestMethod `
    -Method Get `
    -Uri "$base/student/rooms/$roomId/seats?date=$date&start_time=14:00:00&end_time=16:00:00" `
    -Headers $studentHeaders

$releasedSeats.items | Format-Table seat_id, seat_code, status
```

通过标准：

- 未签到提醒第一次包含该预约 ID，第二次为空。
- 超时释放第一次包含该预约 ID，第二次为空。
- 预约状态变为 `EXPIRED`。
- 该座位重新可用。
- 违约记录只生成一条。

## 6. 管理端核对

### 6.1 预约记录

入口：

```text
管理首页 -> 预约记录
```

核对：

- 正常履约预约状态为 `CHECKED_IN`。
- 未签到预约状态为 `EXPIRED`。
- 用户、房间、座位和时间段正确。

### 6.2 违约记录

入口：

```text
管理首页 -> 违约记录
```

核对：

- 能看到该学生的未签到违约。
- 同一未签到预约只出现一条违约记录。

### 6.3 统计查询

入口：

```text
管理首页 -> 统计查询
```

核对：

- 日期范围覆盖本轮验收日期。
- 统计体现正常履约预约的使用时长。
- 统计体现未签到流程产生的违约数量。

### 6.4 通知日志核对

可以通过管理端“通知日志”页面查看日志、通道状态和失败原因。管理端不提供任务执行入口；手动验收如需加速时间线，只能按上文使用 scheduler `tick` 和固定 `ACCEPTANCE_NOW`。

如果需要直接查真实通知日志：

```powershell
docker compose exec -T db psql -U spm -d spm -c "SELECT id, reservation_id, notification_type, channel, status, sent_at FROM notification_logs ORDER BY id DESC LIMIT 20;"
```

通过标准：

- `RESERVATION_REMINDER` 对正常履约预约只生成一条。
- `NO_SHOW_REMINDER` 对未签到预约只生成一条。
- `AUTO_CANCEL_NOTICE` 对超时未签到释放预约只生成一条，页面和邮件文案应显示为“预约过期释放通知”或“超时未签到释放通知”。
- 如果启用 `smtp_email`，目标邮箱能收到对应邮件。
- 如果未收到邮件，管理端通知日志能看到对应预约是否没有触发、发送失败或仍使用 `mock` 通道。

## 7. 失败时如何记录

不通过时不要在本指南里修改内容，请打开：

```text
docs/delivery/manual_scenario_acceptance_record.md
```

记录方式：

- 通过：点击或改写对应复选框为 `[x]`。
- 不通过：在“失败截图区”粘贴截图，并写一句现象。
- 阻塞：在“最终结论”勾选 `BLOCKED`，并把阻塞截图贴到失败截图区。

## 8. 常见问题

### 管理端看不到“院系管理”

通常是本地 PostgreSQL 没有执行最新 migration，或后端没重启。

执行：

```powershell
$env:DATABASE_URL='postgresql+psycopg://spm:spm@127.0.0.1:5432/spm'
alembic upgrade head
```

然后重启后端、退出并重新登录。

### 页面能打开，但学生看不到院系专属自习室

优先检查：

- 学生账号是否选择了正确院系。
- 自习室是否选择同一个院系。
- 自习室是否启用。
- 座位是否启用。

### 创建预约失败

优先检查：

- 预约日期是否是未来日期。
- 预约时间是否在自习室开放时间内。
- 时间是否为 30 分钟粒度，也就是分钟只允许为 `00` 或 `30`。
- 同一座位同一时间段是否已有未取消预约。

### 提醒任务没有发邮件

优先检查：

- `.env` 中 `NOTIFICATION_DEFAULT_CHANNEL` 是否为 `smtp_email`。
- 学生账号是否填写通知邮箱。
- QQ 邮箱 SMTP 授权码是否仍有效。
- 是否已启用 `TASK_SCHEDULER_ENABLED`，或是否已经通过 scheduler `tick` 传入固定时间完成验收模拟。

如果本轮只验业务流程，可以使用 `mock` 通道，不必强制验证真实邮件。
