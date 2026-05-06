# Reservation Module Spec

## 1. 任务定位

本文件定义 `reservation` 模块在 `G4` 阶段的实现边界。

本模块是第四交付单元的一部分，负责提供以下核心能力：

- 学生创建预约
- 学生主动取消预约
- 管理员代预约
- 管理员代取消预约
- 管理员预约记录查询
- 历史预约查询
- 预约规则校验
- 冲突校验

## 2. 实现范围

本次实现只包含以下内容：

- `Reservation` 数据模型
- 学生端创建预约接口
- 学生端历史预约查询接口
- 学生端主动取消预约接口
- 管理员端预约记录查询接口
- 管理员端代预约接口
- 管理员端代取消预约接口
- 预约冲突校验
- 预约时长校验
- 预约时间 30 分钟粒度校验
- 预约开始时间必须在当前时间之后

本次实现不包含以下内容：

- 动态码生成
- 签到状态更新
- 超时释放
- 违约记录生成
- 提醒通知
- 独立的“再次预约”新接口

### 2.1 预约时间规则

`reservation` 模块必须固定遵守以下规则：

- 预约开始时间和结束时间必须按 30 分钟粒度提交，即分钟只允许为 `00` 或 `30`，秒和微秒必须为 `0`
- `start_time` 必须早于 `end_time`
- `start_time` 必须晚于当前时间，学生创建预约和管理员代预约都不得创建过去或已经开始的时间段
- 单次预约时长不得超过 `system_config.max_reservation_hours`
- 预约开始时间和结束时间必须落在自习室开放时间范围内
- 学生只能预约自己可见范围内的自习室和座位
- 已注销或未启用的自习室不可预约
- 已注销或未启用的座位不可预约

### 2.2 冲突校验规则

- 同一座位在同一时间段内不允许存在冲突预约
- 冲突校验必须在数据库查询层完成
- 不允许先取出大量预约记录到内存后再做重叠判断

### 2.3 取消规则

- 学生只能取消自己创建的预约
- 学生只能在预约开始前主动取消
- 管理员可以代取消预约
- 取消后预约状态必须更新为 `CANCELLED`
- 学生主动取消和管理员代取消必须记录取消来源

### 2.4 历史复用规则

- 历史预约查询由 `GET /student/reservations/history` 提供
- “再次预约”不新增独立接口
- 前端如需再次预约，使用历史记录中的 `seat_id`、时间信息重新调用创建预约接口
- 历史预约结果必须包含再次预约所需的 `seat_id`、`start_time`、`end_time`

### 2.5 当前有效预约查询规则

- 学生端提供 `GET /student/reservations/current`
- 当前有效预约只包含状态为 `BOOKED` 或 `CHECKED_IN` 且 `end_time` 尚未结束的预约
- 当前有效预约按 `start_time` 升序返回
- 当前有效预约查询必须在数据库查询层完成，不允许先拉全量历史再在内存中过滤

### 2.6 管理端预约记录查询规则

- 管理端提供 `GET /admin/reservations`
- 预约记录查询至少支持 `user_id`、`room_id`、`seat_id`、`status`、`date_from`、`date_to` 条件筛选
- 预约记录查询必须返回管理端可直接展示的预约列表结果，不得要求页面自行拼装数据库语义
- 预约记录查询必须在数据库查询层完成筛选与排序，不允许先拉取全量记录再在内存中过滤

### 2.7 状态边界

- 本阶段 `reservation` 只负责创建 `BOOKED` 和取消为 `CANCELLED`
- `CHECKED_IN` 状态由 `checkin` 模块负责
- `EXPIRED` 状态由后续签到超时链路负责
- `reservation` 在 `G4` 阶段不得承担签到、违约、提醒逻辑

## 3. 模块边界

- `reservation` 可以依赖 `identity` 获取当前用户身份、院系和管理端权限信息
- `reservation` 可以依赖 `resource` 获取自习室、座位、可见性和开放时间信息
- `reservation` 可以依赖 `system_config` 获取预约时长参数
- `reservation` 不依赖 `checkin`
- `reservation` 不依赖 `violation`
- `reservation` 不依赖 `notification`

跨模块协作规则固定如下：

- 院系访问限制由 `identity` 和 `resource` 的公开 service 提供，`reservation` 不重复实现权限规则
- 自习室和座位是否存在、是否启用、是否可见，由 `resource` 提供判断结果
- 最大预约时长由 `system_config` 提供
- `reservation` 不直接调用其他模块的 repository
- `reservation` 不直接修改其他模块 model 状态

## 4. 预约规则

预约规则固定如下：

### 4.1 学生预约

- 学生创建预约时，`created_by` 记录为学生本人
- 学生只能为自己创建预约
- 学生不能通过本模块替其他学生创建预约

### 4.2 管理员代预约

- 管理员可以为指定学生代预约
- 管理员代预约时，`created_by` 记录为管理员
- 代预约仍必须通过同样的时间、冲突、资源可用性校验

### 4.3 学生取消

- 学生主动取消时，`cancelled_by` 记录为学生本人
- 学生取消必须填写 `reason`

### 4.4 管理员代取消

- 管理员代取消时，`cancelled_by` 记录为管理员
- 管理员代取消可以处理非本人创建的预约

## 5. 数据模型范围

本模块使用以下实体：

- `Reservation`

本模块必须保证以下数据规则：

- `user_id` 必须指向有效用户
- `seat_id` 必须指向有效座位
- `room_id` 必须指向有效自习室
- `start_time < end_time`
- `status` 只允许使用已定义状态枚举
- `cancel_reason` 在取消路径上可记录原因

## 6. 对外接口

本模块在 `G4` 阶段实现以下接口：

### 学生端

- `POST /student/reservations`
- `GET /student/reservations/current`
- `GET /student/reservations/history`
- `POST /student/reservations/{reservation_id}/cancel`

### 管理端

- `GET /admin/reservations`
- `POST /admin/reservations`
- `POST /admin/reservations/{reservation_id}/cancel`

## 7. 代码边界

目录固定如下：

```text
app/modules/reservation/
  api/
  models/
  schemas/
  repositories/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责预约规则、取消规则、冲突校验和历史查询编排
- `repositories` 负责预约查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `reservation` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/reservation/models/reservation.py

app/modules/reservation/schemas/reservation.py

app/modules/reservation/repositories/reservation_repository.py

app/modules/reservation/services/reservation_service.py
app/modules/reservation/services/conflict_service.py
app/modules/reservation/services/history_service.py

app/modules/reservation/api/student_reservation.py
app/modules/reservation/api/admin_reservation.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `Reservation` 数据模型
2. 建立 reservation schema
3. 建立 reservation repository
4. 建立冲突校验与规则校验 service
5. 建立学生端创建预约接口
6. 建立学生端历史预约查询与取消接口
7. 建立管理员端预约记录查询、代预约与代取消接口
8. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 学生可成功创建预约
- `09:30-10:30` 等 30 分钟粒度预约可创建
- 非 `00/30` 分钟粒度预约被拒绝
- 过去时间段预约被拒绝，学生创建和管理员代预约都必须覆盖
- 超过最大预约时长的预约被拒绝
- 超出自习室开放时间的预约被拒绝
- 不可见自习室或座位的预约被拒绝
- 已注销或未启用资源的预约被拒绝
- 同一座位冲突预约被拒绝
- 学生可查询当前有效预约
- 学生可查询自己的历史预约
- 历史预约结果可支撑再次预约
- 学生可在预约开始前主动取消
- 学生在预约开始后主动取消被拒绝
- 学生取消他人预约被拒绝
- 管理员可查询预约记录
- 管理员可代预约
- 管理员可代取消

## 11. 完成标准

`reservation` 模块在 `G4` 阶段完成时，必须满足：

- 学生可以创建预约
- 学生可以查询当前有效预约
- 学生可以取消未开始的预约
- 学生可以查询历史预约
- 历史预约结果可复用为再次预约输入
- 管理员可以查询预约记录
- 管理员可以代预约和代取消
- 冲突校验可用
- 预约规则校验可用
- 关键预约测试通过
