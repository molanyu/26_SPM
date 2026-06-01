# Checkin Module Spec

## 1. 任务定位

本文件定义 `checkin` 模块在 `G5` 阶段的实现边界。

本模块是第五交付单元的一部分，负责提供以下核心能力：

- 自习室绑定的 5 分钟动态签到码派生与校验
- 动态码签到
- 二维码签到
- 签到校验
- 签到成功后的预约状态更新
- 超时未签到预约的释放

## 2. 实现范围

本次实现只包含以下内容：

- `CheckinRecord` 数据模型；`CheckinCode` 仅作为历史兼容或审计表保留，不作为当前签到码来源
- 自习室绑定的 5 分钟动态签到码只读派生能力
- 学生端动态码签到接口
- 学生端二维码签到接口
- 签到有效性校验
- 签到成功后将预约状态更新为 `CHECKED_IN`
- 超时未签到预约的释放任务
- 管理端最小动态签到码页面，支持查看指定自习室当前动态码状态、有效至时间和签到记录

本次实现不包含以下内容：

- 预约创建与取消
- 预约历史查询
- 预约提醒发送
- 违约记录查询
- 违约统计
- 复杂签到大盘、批量补签或人工代签到

### 2.1 签到对象范围

- 只有已存在且状态为 `BOOKED` 的预约才允许进入签到校验
- 学生只能对自己的预约执行签到
- 已取消、已签到、已过期的预约不得再次签到

### 2.2 签到时间规则

- 签到必须发生在预约有效签到窗口内
- `checkin_grace_minutes` 由 `system_config` 提供
- 超过签到宽限时间的未签到预约不再允许签到
- 到达超时释放阈值后，预约必须由内部任务更新为 `EXPIRED`
- 超时释放任务必须由后台调度器自动扫描触发，不得依赖管理员手动执行
- 自动化测试可通过 injected now 或 scheduler `tick/run_once` 模拟时间推进，不依赖真实等待

### 2.3 动态码与二维码规则

- 系统必须支持为每个自习室按 `room_id + 5分钟时间片 + 服务端密钥/稳定算法` 派生动态签到码
- 同一自习室在同一 5 分钟时间片内码值稳定
- 同一自习室跨 5 分钟时间片码值必须变化
- 不同自习室在同一时间片内码值必须不同
- 当前动态码不需要管理员生成，不依赖每日落表记录作为来源
- 二维码签到本质上是对同一签到信息的另一种提交方式
- 二维码 token 的实现形式可为签名 token，不要求单独落表
- 二维码 token 必须与自习室和短时有效期绑定，不应默认有效到当天结束
- 动态码或二维码都必须与预约所属自习室匹配

### 2.4 超时释放边界

- 超时释放只负责将预约状态更新为 `EXPIRED`
- 违约记录生成不由 `checkin` 模块直接负责
- 需要记录违约时，`checkin` 通过 `violation` 的公开 service 触发后续落账
- 预约开始后 10 分钟提醒不属于 `checkin` 的职责，提醒由 `notification` 负责

## 3. 模块边界

- `checkin` 可以依赖 `reservation` 获取预约信息并更新预约状态
- `checkin` 可以依赖 `resource` 获取自习室与座位信息
- `checkin` 可以依赖 `system_config` 获取签到宽限与超时释放参数
- `checkin` 不依赖 `notification`
- `checkin` 不直接写 `violation` 的数据表

跨模块协作规则固定如下：

- 预约是否存在、预约当前状态、预约所属用户，由 `reservation` 的公开 service 提供
- 自习室是否存在、动态码所属房间是否匹配，由 `resource` 的公开 service 提供
- 超时未签到后的违约落账，必须通过 `violation` 的公开 service 触发
- `checkin` 不直接调用其他模块的 repository
- `checkin` 不直接修改其他模块 model 状态，预约状态更新必须通过 `reservation` 的公开 service 完成

## 4. 签到规则

签到规则固定如下：

### 4.1 动态码签到

- `POST /student/checkins/code` 必须接收 `reservation_id` 和 `code`
- 动态码必须与预约所属自习室、当天日期和有效期一致
- 校验成功后创建有效签到记录，并将预约状态更新为 `CHECKED_IN`

### 4.2 二维码签到

- `POST /student/checkins/qrcode` 必须接收 `reservation_id` 和 `token`
- 二维码 token 必须能解析或验证出与预约一致的签到信息
- 校验成功后创建有效签到记录，并将预约状态更新为 `CHECKED_IN`

### 4.3 签到记录

- 每次成功签到必须写入 `CheckinRecord`
- `checkin_method` 只允许 `CODE` 或 `QRCODE`
- 非法签到尝试不得写入有效签到记录
- 同一预约成功签到后不得再次生成第二条有效签到记录

### 4.4 超时释放

- 超时释放任务必须扫描仍处于 `BOOKED` 状态且超过阈值的预约
- 满足超时条件的预约必须更新为 `EXPIRED`
- 满足超时条件后如需违约记录，调用 `violation` 公开 service

## 5. 数据模型范围

本模块使用以下实体：

- `CheckinCode`（历史兼容或审计表，当前动态码不得依赖该表生成或校验）
- `CheckinRecord`

本模块必须保证以下数据规则：

- 当前动态码由 service 基于自习室、5 分钟时间片和服务端密钥派生，不要求写入 `CheckinCode`
- 如历史兼容流程仍读取 `CheckinCode`，不得将其作为当前动态码校验依据
- `CheckinRecord.reservation_id` 必须指向有效预约
- `CheckinRecord.user_id` 必须与预约所属用户一致
- `CheckinRecord.room_id` 和 `seat_id` 必须与预约一致
- `CheckinRecord.is_valid` 用于标识签到记录有效性

## 6. 对外接口与内部任务

本模块在 `G5` 阶段实现以下入口：

### 学生端接口

- `POST /student/checkins/code`
- `POST /student/checkins/qrcode`

### 内部任务

- 动态签到码按需派生，不设置每日生成任务作为当前码来源
- 后台调度器自动执行超时释放

### 管理端页面

- `GET /admin/checkins`

说明：

- 预约开始后 10 分钟提醒由 `notification` 模块实现，不属于本模块接口
- 违约记录查询与统计不属于本模块接口
- 管理端页面只调用 `checkin` 公开 service，不直接操作 repository；页面用于只读观测、验收核对和排障，不推进签到码生成、签到、补签或代签到流程

## 7. 代码边界

目录固定如下：

```text
app/modules/checkin/
  api/
  models/
  schemas/
  repositories/
  services/
  tasks/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责签到校验、状态流转编排和超时释放编排
- `repositories` 负责签到码和签到记录的查询与写入
- `models` 只定义表结构
- `tasks` 不负责生成当前签到码；动态码由 service 按需派生，`tasks` 仅负责超时释放触发等后台流程
- 不允许其他模块直接操作 `checkin` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/checkin/models/checkin_code.py
app/modules/checkin/models/checkin_record.py

app/modules/checkin/schemas/checkin.py

app/modules/checkin/repositories/checkin_code_repository.py
app/modules/checkin/repositories/checkin_record_repository.py

app/modules/checkin/services/checkin_service.py
app/modules/checkin/services/code_service.py
app/modules/checkin/services/timeout_service.py

app/modules/checkin/api/student_checkin.py

app/modules/checkin/tasks/daily_code_task.py
app/modules/checkin/tasks/timeout_release_task.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `CheckinCode`、`CheckinRecord` 数据模型
2. 建立 checkin schema
3. 建立签到码与签到记录 repository
4. 建立动态码生成与签到校验 service
5. 建立学生端签到接口
6. 建立超时释放 service 与 tasks
7. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 同一自习室同一 5 分钟窗口动态码稳定
- 同一自习室跨 5 分钟窗口动态码变化
- 不同自习室同一时间片动态码不同
- 学生可通过正确动态码完成签到
- 学生可通过正确二维码 token 完成签到
- 错误动态码签到失败
- 非本人预约签到失败
- 已取消预约签到失败
- 已过期预约签到失败
- 同一预约重复签到失败
- 成功签到后预约状态更新为 `CHECKED_IN`
- 超过签到宽限时间后签到失败
- 超时释放任务会将超时未签到预约更新为 `EXPIRED`
- scheduler tick 可按 injected now 触发超时释放，不依赖管理端按钮或真实等待
- 超时释放后会调用违约落账协作入口

## 11. 完成标准

`checkin` 模块在 `G5` 阶段完成时，必须满足：

- 学生可以通过动态码签到
- 学生可以通过二维码签到
- 签到成功后预约状态正确更新
- 5 分钟动态签到码派生和校验可用
- 超时未签到预约可被后台调度器自动释放
- 管理端可查看指定自习室当前动态码状态、有效至时间和签到记录
- 管理端可查看签到记录
- 关键签到测试通过
