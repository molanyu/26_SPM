# 数据模型

## 1. 文档定位

本文件定义项目的数据模型边界。

本文件只回答以下问题：

- 系统有哪些核心实体
- 每个实体有哪些关键字段
- 实体之间是什么关系
- 哪些约束必须由数据库和模型层保证

本文件不定义接口路径，不定义页面行为，不定义具体 SQL 实现细节。

## 2. 建模原则

- 实体命名统一使用业务含义
- 字段命名保持直接、稳定、可读
- 公共字段只保留必要部分
- 状态字段优先使用明确枚举，不使用模糊字符串
- 关系优先使用清晰外键，不做隐式关联
- 非必要不建立复杂继承层次

## 3. 核心实体

### 3.1 Department

职责：

- 表示院系
- 控制院系自习室的访问范围

关键字段：

- `id`
- `name`
- `code`
- `is_active`

### 3.2 User

职责：

- 表示系统用户
- 支持学生与管理员统一建模

关键字段：

- `id`
- `student_no`
- `name`
- `email`
- `password_hash`
- `department_id`
- `is_active`
- `last_login_at`
- `created_at`
- `updated_at`

说明：

- 学生和管理员统一使用 `User`
- 角色能力由角色关系决定，不在 `User` 中硬编码身份类型
- 学生登录标识使用 `student_no`
- 管理员登录标识使用 `email`
- 学生可选使用 `email` 保存通知邮箱，但该邮箱不是学生登录标识
- 通知模块读取 `User.email` 作为邮件通知目标；学生未填写通知邮箱时，真实邮件通道应受控失败并落通知日志

### 3.3 Role

职责：

- 表示角色

关键字段：

- `id`
- `name`
- `code`
- `description`
- `is_active`

### 3.4 Permission

职责：

- 表示权限点

关键字段：

- `id`
- `name`
- `code`
- `description`

### 3.5 UserRole

职责：

- 表示用户与角色的多对多关系

关键字段：

- `id`
- `user_id`
- `role_id`

### 3.6 RolePermission

职责：

- 表示角色与权限的多对多关系

关键字段：

- `id`
- `role_id`
- `permission_id`

### 3.7 StudyRoom

职责：

- 表示自习室

关键字段：

- `id`
- `name`
- `location`
- `department_id`
- `is_department_only`
- `is_active`
- `open_time`
- `close_time`
- `created_at`
- `updated_at`

说明：

- `department_id` 为空时表示公共自习室
- `is_department_only` 为真时，只允许对应院系学生使用

### 3.8 Seat

职责：

- 表示自习室内座位

关键字段：

- `id`
- `room_id`
- `seat_code`
- `seat_label`
- `is_active`
- `is_window_side`
- `has_power_socket`
- `has_track_socket`
- `created_at`
- `updated_at`

约束：

- 同一自习室内 `seat_code` 唯一

### 3.9 Reservation

职责：

- 表示预约记录

关键字段：

- `id`
- `user_id`
- `seat_id`
- `room_id`
- `start_time`
- `end_time`
- `status`
- `created_by`
- `cancelled_by`
- `cancel_reason`
- `created_at`
- `updated_at`

状态枚举：

- `BOOKED`
- `CHECKED_IN`
- `CANCELLED`
- `EXPIRED`

说明：

- `created_by` 用于标识是否为管理员代预约
- `cancelled_by` 用于标识取消操作来源

约束：

- `start_time < end_time`
- 单次预约时长不得超过系统参数限制
- 座位在同一时间段内不允许存在冲突预约

### 3.10 CheckinCode（历史兼容）

职责：

- 历史兼容或审计用途的签到码记录
- 当前签到码不得依赖该表作为生成或校验来源
- 当前签到码由 `checkin` service 基于 `room_id + 5分钟时间片 + 服务端密钥/稳定算法` 派生

关键字段：

- `id`
- `room_id`
- `code`
- `code_date`
- `expires_at`
- `created_at`

约束：

- 保留既有字段和约束用于旧数据兼容
- 新的当前动态码逻辑不要求写入 `CheckinCode`
- 同一自习室同一 5 分钟时间片内当前码稳定，跨时间片必须变化

### 3.11 CheckinRecord

职责：

- 表示签到记录

关键字段：

- `id`
- `reservation_id`
- `user_id`
- `room_id`
- `seat_id`
- `checkin_method`
- `checkin_at`
- `is_valid`
- `created_at`

状态说明：

- `checkin_method` 取值为 `CODE` 或 `QRCODE`

### 3.12 ViolationRecord

职责：

- 表示违约记录

关键字段：

- `id`
- `user_id`
- `reservation_id`
- `violation_type`
- `occurred_at`
- `remark`
- `created_at`

说明：

- 当前阶段至少支持“预约超时未签到”类型

### 3.13 SystemConfig

职责：

- 表示全局配置项

关键字段：

- `id`
- `config_key`
- `config_value`
- `value_type`
- `description`
- `updated_at`

说明：

- 使用键值方式存储系统参数
- 由 service 层负责转换为业务配置

### 3.14 NotificationLog

职责：

- 表示通知发送记录

关键字段：

- `id`
- `user_id`
- `reservation_id`
- `notification_type`
- `channel`
- `sent_at`
- `status`
- `message`

## 4. 实体关系

实体关系固定如下：

- `Department` 1 -> N `User`
- `Department` 1 -> N `StudyRoom`
- `User` N -> N `Role`，通过 `UserRole`
- `Role` N -> N `Permission`，通过 `RolePermission`
- `StudyRoom` 1 -> N `Seat`
- `User` 1 -> N `Reservation`
- `Seat` 1 -> N `Reservation`
- `StudyRoom` 1 -> N `Reservation`
- `StudyRoom` 1 -> N `CheckinCode`（历史兼容记录；当前动态码不依赖该关系）
- `Reservation` 1 -> 0..1 `CheckinRecord`
- `Reservation` 1 -> 0..1 `ViolationRecord`
- `Reservation` 1 -> N `NotificationLog`

## 5. 必要约束

以下约束必须在数据库约束、模型约束或 service 校验中保证：

- 同一自习室内座位编号唯一
- 预约开始时间必须早于结束时间
- 单次预约时长不得超过系统参数
- 同一座位在重叠时间段内不能被重复预约
- 仅允许已预约状态进入签到
- 超时未签到的预约必须转为失效并生成违约记录
- 院系限定自习室只允许对应院系学生预约
- 管理员用户必须存在可用 `email`
- 学生用户必须存在可用 `student_no`
- 学生通知邮箱为可选字段；如提供，必须格式可用且不得与现有 `User.email` 重复
- 所有可登录用户必须存在 `password_hash`

## 6. 状态规则

### Reservation.status

状态流转固定如下：

- `BOOKED -> CHECKED_IN`
- `BOOKED -> CANCELLED`
- `BOOKED -> EXPIRED`

禁止流转：

- `CHECKED_IN -> BOOKED`
- `CANCELLED -> BOOKED`
- `EXPIRED -> BOOKED`

### NotificationLog.status

状态取值：

- `PENDING`
- `SENT`
- `FAILED`

## 7. 删除规则

- 业务主表默认使用软删除或 `is_active` 控制可用性
- 预约、签到、违约、通知记录不允许物理删除
- 自习室和座位注销后，不删除历史记录
- 角色和权限调整不影响历史业务数据
- 角色停用通过 `is_active=false` 实现，用于禁用或下线角色
- 角色删除只允许删除未分配给任何用户、非系统保留角色的角色
- 第一版系统保留角色固定按 `Role.code == "system_admin"` 判定，不新增数据字段；`system_admin` 即使未分配用户也不得删除
- 删除角色时必须清理该角色的 `role_permissions` 绑定，但不得删除 `users` 或 `permissions`
- 如果角色存在 `user_roles` 分配，必须拒绝删除并要求先解除分配或停用角色

## 8. 后续拆分规则

后续如果新增字段或实体，必须先确认：

- 是否属于现有模块职责
- 是否改变现有实体关系
- 是否改变预约主状态流转

确认后先修改本文件，再修改代码。
