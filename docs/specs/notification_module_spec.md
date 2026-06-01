# Notification Module Spec

## 本轮验收阻塞修正规则

以下规则用于修复手动验收中发现的“等待真实时间后没有提醒、没有超时未签到释放、没有违约落账”问题：

- 本地真实联调和生产部署若要依赖真实时间自动推进，必须显式启用 `TASK_SCHEDULER_ENABLED=true`；关闭时系统不会自动发送提醒、释放超时未签到预约或落违约。
- 调度器晚启动或某一轮 tick 延迟时，不得因为只扫描严格 1 分钟窗口而漏掉已经满足条件且尚未成功发送过的未签到提醒。
- 未签到提醒的有效候选应理解为：预约状态仍为 `BOOKED`、预约开始时间已经早于或等于当前时间减 10 分钟、且该预约尚未成功发送过 `NO_SHOW_REMINDER`。
- 预约前提醒可以对仍未开始、已经进入开始前 15 分钟提醒范围且尚未成功发送过提醒的预约补发；预约已经开始后不再补发预约前提醒。
- 超时未签到释放必须由后台调度器自动执行；管理端只能查询通知日志和任务状态，不得提供用于推进业务流程的手动触发按钮。
- 测试必须覆盖调度器延迟/晚启动后的补扫场景，以及同一预约同一通知类型的幂等性。

## 1. 任务定位

本文件定义 `notification` 模块第一版实现的边界。

本模块在当前阶段负责提供以下基础能力：

- 预约前提醒
- 未签到提醒
- 超时未签到释放后的通知
- 通知发送记录落账

## 2. 实现范围

本次实现只包含以下内容：

- `NotificationLog` 数据模型
- 预约开始前 15 分钟提醒任务
- 预约开始后 10 分钟未签到提醒任务
- 预约因超时未签到被释放后的通知任务
- 后台自动任务调度器
- 通知发送 service
- SMTP 邮件发送通道
- 通知发送记录查询基础能力

本次实现不包含以下内容：

- 真实微信订阅消息接入
- 用户通知偏好设置
- 管理端通知运营页面
- 通知模板管理后台

### 2.1 首版发送通道

第一版固定采用以下策略：

- 保留 `channel` 字段
- 首版同时支持 `mock` 与 `smtp_email` 两种通道
- 默认开发与自动化测试环境可继续使用 `mock`
- 当显式启用 `smtp_email` 时，通知服务必须通过真实 SMTP 通道发送邮件
- 通知必须落 `NotificationLog`
- 目标用户缺少可用邮箱地址时，SMTP 发送必须受控失败并记录失败结果，不得静默伪造成成功
- SMTP 配置缺失或非法时，发送必须受控失败并记录失败结果，不得自动回退为 `mock`
- 后续如接入真实微信，只能在本模块内部扩展，不影响外部模块接口

### 2.2 首版通知类型

第一版固定支持以下通知类型：

- `RESERVATION_REMINDER`
- `NO_SHOW_REMINDER`
- `AUTO_CANCEL_NOTICE`

说明：

- `RESERVATION_REMINDER`：预约开始前 15 分钟提醒
- `NO_SHOW_REMINDER`：预约开始后 10 分钟仍未签到的提醒
- `AUTO_CANCEL_NOTICE`：内部枚举名，对应“超时未签到释放通知”；不是用户主动取消或管理员代取消

### 2.3 自动调度与测试时钟

通知任务必须由后台调度器自动扫描和触发，不得依赖管理员在页面上手动点击。

规则固定如下：

- 应用启动后可按配置启动通知调度器。
- 调度器按固定短周期执行一次任务扫描，默认粒度为 1 分钟。
- 每轮调度应自动执行预约前提醒、未签到提醒、超时未签到释放通知三类任务。
- 调度器必须复用现有任务幂等规则，重复扫描不得重复生成成功通知。
- 调度器启停和扫描间隔必须可通过配置控制，测试环境必须能关闭真实后台循环。
- 自动化验收不得通过管理端按钮推进任务；应使用可注入时钟或一次性 `tick/run_once` 入口，在测试中传入固定 `now` 来模拟时间推进。
- 生产或本地真实联调使用系统真实时间；测试中使用 fake clock / injected now / scheduler tick 是工程上推荐做法。

## 3. 通知规则

通知规则固定如下：

### 3.1 预约前提醒规则

- 只对状态仍为 `BOOKED` 的预约发送
- 只在预约开始前 15 分钟窗口内触发
- 同一预约同一通知类型只允许生成一次成功通知记录

### 3.2 未签到提醒规则

- 只对状态仍为 `BOOKED` 且尚未签到的预约发送
- 只在预约开始后 10 分钟触发
- 已签到或已取消预约不得发送未签到提醒
- 同一预约同一通知类型只允许生成一次成功通知记录

### 3.3 超时未签到释放通知规则

- 只对已被释放或已过期的预约发送
- 超时未签到释放通知必须在预约状态完成更新后触发
- 同一预约同一通知类型只允许生成一次成功通知记录

### 3.4 幂等性规则

- 同一预约、同一通知类型、同一轮任务重复执行时，不得重复生成成功通知
- 任务扫描和发送必须具备幂等性

### 3.5 邮件内容规则

当通道为 `smtp_email` 时，邮件内容必须满足以下规则：

- 邮件标题必须使用中文，且能区分 `RESERVATION_REMINDER`、`NO_SHOW_REMINDER`、`AUTO_CANCEL_NOTICE`
- 邮件正文必须使用中文为主，不使用仅面向开发者的英文调试文案
- 邮件正文必须至少包含预约 ID、预约开始时间、预约结束时间
- 如上游快照已提供自习室、座位等信息，正文应包含自习室和座位信息
- `RESERVATION_REMINDER` 正文应明确提示预约即将开始
- `NO_SHOW_REMINDER` 正文应明确提示预约已开始且仍未签到
- `AUTO_CANCEL_NOTICE` 正文应明确提示预约因超时未签到被置为过期/释放座位，不得表述为用户主动取消
- 邮件正文不得包含原始密码、`password_hash`、SMTP 授权码或其他敏感配置

## 4. 模块边界

- `notification` 可以依赖 `reservation`
- `notification` 可以依赖 `checkin`
- `notification` 可以依赖 `violation`
- `notification` 可以依赖 `identity`
- `notification` 不依赖 `resource`
- `notification` 不依赖 `system_config`

跨模块协作规则固定如下：

- 预约开始时间、预约当前状态由 `reservation` 的公开 service 提供
- 是否已经签到由 `reservation` 当前状态或 `checkin` 公开 service 提供
- 超时未签到释放后的违约落账是否完成，可通过 `violation` 的公开 service 或查询结果辅助判断
- 目标用户的邮箱地址、启用状态等只读信息由 `identity` 的公开查询能力提供
- `notification` 不直接调用其他模块的 repository
- `notification` 不直接修改其他模块 model 状态

## 5. 数据模型范围

本模块使用以下实体：

- `NotificationLog`

本模块必须保证以下数据规则：

- `user_id` 必须指向有效用户
- `reservation_id` 必须指向有效预约
- `notification_type` 必须使用已定义枚举
- `channel` 必须记录发送通道
- `status` 必须记录发送结果
- `sent_at` 必须记录发送时间
- `smtp_email` 通道仅在目标用户存在可用 `email` 时允许发送成功

建议唯一性规则：

- 同一 `reservation_id + notification_type + status=SUCCESS` 不应重复出现

## 6. 对外入口

本模块第一版不提供外部 HTTP 接口。

本模块仅提供以下内部任务与公开 service：

### 内部任务

- `send_reservation_reminders`
- `send_no_show_reminders`
- `send_auto_cancel_notifications`
- 自动调度器 `tick/run_once`

### 公开 service

- `send_notification(notification_type, reservation_id, user_id, message)`

说明：

- 第一版重点是任务触发和发送记录，不做前台页面
- `admin_portal` 只允许提供通知日志查看与筛选，不允许提供通知任务手动触发入口
- 本地验收或自动化测试如需加速时间，只能通过内部测试辅助入口、可注入时钟或 scheduler `tick/run_once` 完成，不得通过管理端页面推进业务流程
- 页面必须展示通知日志的 `reservation_id`、通知类型、通道、状态、发送时间和失败原因可定位信息

## 7. 代码边界

目录固定如下：

```text
app/modules/notification/
  tasks/
  services/
  models/
  repositories/
  schemas/
```

边界规则如下：

- `tasks` 负责扫描待触发通知
- `services` 负责通知发送、幂等校验、消息组装
- `repositories` 负责通知日志查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `notification` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/notification/models/notification_log.py

app/modules/notification/schemas/notification.py

app/modules/notification/repositories/notification_repository.py

app/modules/notification/services/notification_service.py
app/modules/notification/services/email_sender.py
app/modules/notification/services/reminder_service.py
app/modules/notification/services/scheduler_service.py

app/modules/notification/tasks/reservation_reminder_task.py
app/modules/notification/tasks/no_show_reminder_task.py
app/modules/notification/tasks/auto_cancel_notice_task.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `NotificationLog` 数据模型
2. 建立 notification schema
3. 建立 notification repository
4. 建立通知发送与幂等校验 service
5. 建立预约前提醒任务
6. 建立未签到提醒任务
7. 建立超时未签到释放通知任务
8. 建立后台自动调度器
9. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 预约开始前 15 分钟会生成预约前提醒
- 非目标时间窗口不会发送预约前提醒
- 预约开始后 10 分钟且仍未签到时会生成未签到提醒
- 已签到预约不会发送未签到提醒
- 已取消预约不会发送未签到提醒
- 超时未签到导致预约过期释放后，会生成超时未签到释放通知
- 同一预约同一通知类型不会重复生成成功通知
- 通知发送会落 `NotificationLog`
- `smtp_email` 通道在配置完整且目标用户具备邮箱时可走真实发送路径
- 目标用户缺少邮箱地址时，SMTP 发送受控失败
- SMTP 配置缺失时，SMTP 发送受控失败
- 通知任务重复执行时保持幂等
- 后台调度器每轮 tick 会自动执行三类通知任务
- 测试可通过 injected now / run_once 模拟时间推进，不依赖真实等待
- SMTP 邮件标题和正文格式符合邮件内容规则

## 11. 完成标准

`notification` 模块第一版完成时，必须满足：

- 预约前提醒任务可用
- 未签到提醒任务可用
- 超时未签到释放通知任务可用
- 后台调度器可按配置自动运行通知任务
- 通知发送记录可落账
- `smtp_email` 真实邮件通道可在显式配置后启用
- 管理端可查看通知日志，用于解释未收到邮件或日志缺失的原因；管理端不得手动触发通知任务
- 自动化测试可通过 scheduler `tick/run_once` 和 injected now 模拟时间推进
- 关键通知测试通过
- 邮件模板内容测试通过
