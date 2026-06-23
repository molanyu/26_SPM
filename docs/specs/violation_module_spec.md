# Violation Module Spec

## 1. 任务定位

本文件定义 `violation` 模块第一版实现的边界。

本模块在当前阶段负责提供以下基础能力：

- 违约记录落账
- 违约记录查询
- 用户级违约次数统计
- 对 `checkin` 提供违约落账公开 service
- 对 `reservation` 提供统一预约限制状态只读 service

## 2. 实现范围

本次实现只包含以下内容：

- `ViolationRecord` 数据模型
- `UserReservationBlock` 数据模型
- 超时未签到违约记录生成
- 管理端违约记录查询接口
- 管理端用户级违约次数统计
- 管理端手动开启和解除用户预约限制
- 对 `checkin` 暴露的违约落账 service
- 违约累计与惩罚资格查询规则

本次实现不包含以下内容：

- 自习室/座位使用率统计
- 提醒通知
- 管理端统计大盘
- 复杂违约类型体系
- 多级惩罚、人工申诉、惩罚豁免和信用分体系

### 2.1 当前支持的违约类型

第一版固定只支持以下违约类型：

- `NO_SHOW_TIMEOUT`

说明：

- 该类型表示预约开始后，用户在允许阈值内未完成签到，预约被释放并记录违约

### 2.2 违约生成规则

- 只有超时未签到释放的预约允许生成违约记录
- 学生主动取消预约不得生成违约记录
- 已签到预约不得生成违约记录
- 同一预约最多只能生成一条 `NO_SHOW_TIMEOUT` 违约记录

### 2.3 违约查询规则

- 管理端必须支持查询违约记录
- 查询至少支持以下过滤条件：
  - `user_id`
  - `student_no`
  - `room_id`
  - `date_from`
  - `date_to`
- 所有过滤条件均为可选项，无筛选条件时默认分页返回全部违约记录
- `user_id`、`student_no`、`room_id`、`date_from`、`date_to` 必须支持任意单独使用或任意组合使用
- 违约查询只返回已经落账的违约记录
- 违约查询页面必须支持用户级违约次数统计，用于展示某个用户已经落账的违约次数
- 用户级违约次数统计只统计已经落账的 `NO_SHOW_TIMEOUT` 记录，并按唯一 `reservation_id` 去重
- 用户级违约次数统计可以随 `user_id` 或 `student_no` 查询条件一起返回；未指定单一用户时不得把该能力扩展为复杂排行或大盘
- 用户级违约次数统计必须基于数据库层聚合完成，不允许先拉取用户全量违约记录后在内存中计数

### 2.4 违约累计与惩罚资格规则

- 违约累计只统计已经落账的 `NO_SHOW_TIMEOUT` 记录
- 同一 `reservation_id` 的重复落账不得重复计入累计次数
- 累计窗口由 `system_config.violation_penalty_window_days` 提供
- 惩罚触发阈值由 `system_config.violation_penalty_threshold_count` 提供
- 惩罚期限由 `system_config.violation_penalty_duration_days` 提供
- 当用户在累计窗口内的违约次数达到阈值时，视为处于惩罚状态
- 惩罚状态的开始时间以触发阈值的最近一条违约 `occurred_at` 为准
- 惩罚状态的结束时间为开始时间加惩罚期限
- 惩罚期结束后，用户恢复预约资格；历史违约记录仍保留，不得物理删除
- 惩罚资格查询必须基于数据库层聚合或筛选完成，不允许先拉取用户全量违约记录后在内存中复杂计算

### 2.5 手动预约限制规则

- 管理员可以在违约记录查询页面针对单个用户手动开启预约限制
- 管理员可以解除该用户当前有效的手动预约限制
- 手动预约限制第一版为无期限限制，开启后持续生效，直到管理员明确解除
- 同一用户同一时间最多只能存在一个有效手动预约限制
- 重复开启已有效的手动预约限制必须幂等处理，不得生成多个有效限制
- 解除不存在的有效手动预约限制必须返回受控业务错误，不得静默伪造解除结果
- 手动预约限制不新增违约记录，不改变 `ViolationRecord` 历史数据
- 手动预约限制状态归属 `violation` 模块，不归属 `system_config`、`identity` 或 `reservation`
- 手动限制原因必须由管理员提交并保存，用于管理端展示和审计
- 解除时必须记录解除管理员和解除时间，不得物理删除历史限制记录
- 手动预约限制不包含申诉、信用分、多级惩罚、批量操作或自动到期能力

## 3. 模块边界

- `violation` 可以依赖 `reservation`
- `violation` 不依赖 `resource`
- `violation` 不依赖 `checkin`
- `violation` 不依赖 `notification`
- `violation` 可以依赖 `system_config` 的公开配置读取 service 获取违约累计与惩罚参数

跨模块协作规则固定如下：

- `checkin` 只能通过 `violation` 的公开 service 触发违约落账
- 其他模块如需判断用户是否处于惩罚状态，只能调用 `violation` 的公开只读 service，不得直接读取 `violation` repository
- `reservation` 创建预约前只能消费 `violation` 提供的统一预约限制状态，不得自行计算自动违约累计或读取手动限制表
- `admin_portal` 只能通过 `violation` 的公开 service 或管理端 API 查询用户统计、开启手动限制和解除手动限制，不得直接写 `violation` repository 或 model
- `violation` 不直接调用 `checkin` 的 repository 或 service
- `violation` 不直接写 `reservation` 的数据状态
- 若违约查询需要按 `room_id` 过滤，过滤条件必须通过 `reservation` 关联关系获得，不允许越过模块边界做跨模块写入
- 若违约查询需要按 `student_no` 过滤，只允许通过 `identity` 用户数据的只读关联完成查询，不允许在 `violation` 中直接修改用户数据

## 4. 违约规则

违约规则固定如下：

### 4.1 落账入口

- `checkin` 超时释放后调用 `violation` 公开 service
- 落账 service 必须验证：
  - 预约存在
  - 预约已处于 `EXPIRED`
  - 预约未存在同类型违约记录

### 4.2 幂等性

- 同一预约重复触发违约落账时，不得生成重复违约记录
- 违约落账 service 必须具备幂等性

### 4.3 查询权限

- 违约记录查询只允许管理员访问
- 违约落账写入不对外暴露 HTTP 入口
- 违约落账只能由内部 service 触发
- 手动预约限制写入允许通过管理端 HTTP 接口暴露，但必须受 `violation.manual_blocks.write` 权限保护

### 4.4 惩罚资格查询

- 惩罚资格查询 service 必须接收 `user_id` 和可选 `as_of`
- 查询结果至少包含：
  - `is_penalized`
  - `restriction_source`
  - `violation_count`
  - `window_start`
  - `window_end`
  - `penalty_start`
  - `penalty_end`
  - `manual_block_id`
  - `manual_block_reason`
  - `manual_block_started_at`
  - `manual_block_created_by`
- 未达到惩罚阈值时，`is_penalized=false`
- 达到惩罚阈值但惩罚期限已过时，`is_penalized=false`
- 存在有效手动预约限制时，`is_penalized=true`
- 自动惩罚有效且手动限制也有效时，`is_penalized=true`，并且结果必须能表达两类来源同时存在
- `restriction_source` 至少能够区分 `NONE`、`AUTO_VIOLATION`、`MANUAL_BLOCK`、`AUTO_AND_MANUAL`
- 惩罚资格查询只读，不得修改 `Reservation`、`ViolationRecord`、`UserReservationBlock` 或用户数据
- 预约拦截由 `reservation` 模块在创建预约前执行，`violation` 只提供只读判断结果

### 4.5 手动预约限制写入

- 手动开启预约限制必须验证目标用户存在
- 手动开启预约限制必须验证操作者是管理员且具备 `violation.manual_blocks.write` 权限
- 手动开启预约限制必须保存目标用户、原因、创建管理员和创建时间
- 手动解除预约限制必须验证目标用户存在
- 手动解除预约限制必须验证操作者是管理员且具备 `violation.manual_blocks.write` 权限
- 手动解除预约限制必须只解除当前有效的手动限制，保留历史记录
- 手动限制写入不得修改 `Reservation`、`ViolationRecord` 或用户数据

## 5. 数据模型范围

本模块使用以下实体：

- `ViolationRecord`
- `UserReservationBlock`

本模块必须保证以下数据规则：

- `user_id` 必须指向有效用户
- `reservation_id` 必须指向有效预约
- `violation_type` 必须使用已定义枚举
- `occurred_at` 必须记录违约发生时间
- 同一 `reservation_id + violation_type` 组合必须唯一
- `UserReservationBlock.user_id` 必须指向有效用户
- `UserReservationBlock.reason` 必须记录管理员填写的限制原因
- `UserReservationBlock.created_by_admin_id` 必须指向执行开启动作的管理员用户
- `UserReservationBlock.created_at` 必须记录开启时间
- `UserReservationBlock.released_by_admin_id` 和 `released_at` 只在解除后填写
- `released_at` 为空表示该手动预约限制当前有效
- 同一用户最多只能存在一条 `released_at IS NULL` 的有效手动预约限制

## 6. 对外接口与公开 service

本模块第一版实现以下入口：

### 管理端接口

- `GET /admin/violations`
- `POST /admin/violations/users/{user_id}/manual-block`
- `POST /admin/violations/users/{user_id}/manual-block/release`

权限：

- `GET /admin/violations` 只保留管理员查询权限语义，不绑定 `violation.manual_blocks.write`
- `POST /admin/violations/users/{user_id}/manual-block` 必须受 `violation.manual_blocks.write` 权限保护
- `POST /admin/violations/users/{user_id}/manual-block/release` 必须受 `violation.manual_blocks.write` 权限保护

### 公开 service

- `record_timeout_violation(reservation_id)`
- `get_user_penalty_status(user_id, as_of=None)`
- `get_user_violation_summary(user_id, as_of=None)`
- `activate_manual_reservation_block(user_id, reason, admin_user_id)`
- `release_manual_reservation_block(user_id, admin_user_id)`

说明：

- 第一版只实现用户级违约次数统计，不实现复杂统计大盘
- 第一版允许管理端通过受 `violation.manual_blocks.write` 保护的明确 HTTP 写接口开启和解除手动预约限制
- 惩罚资格查询不新增学生端 HTTP 入口，只作为跨模块只读 service 使用
- 手动预约限制不新增学生端 HTTP 入口

## 7. 代码边界

目录固定如下：

```text
app/modules/violation/
  api/
  models/
  schemas/
  repositories/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责违约落账、手动限制写入、幂等校验、查询编排和统一预约限制状态组装
- `repositories` 负责违约记录查询与写入、用户级统计聚合、手动限制查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `violation` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/violation/models/violation_record.py
app/modules/violation/models/user_reservation_block.py

app/modules/violation/schemas/violation.py

app/modules/violation/repositories/violation_repository.py
app/modules/violation/repositories/manual_block_repository.py

app/modules/violation/services/violation_service.py
app/modules/violation/services/query_service.py
app/modules/violation/services/manual_block_service.py

app/modules/violation/api/admin_violation.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `ViolationRecord` 数据模型
2. 建立 `UserReservationBlock` 数据模型
3. 建立 violation schema
4. 建立 violation repository
5. 建立手动限制 repository
6. 建立违约落账、用户级统计、手动限制和统一预约限制状态 service
7. 建立管理端查询与手动限制接口
8. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 超时未签到预约可生成违约记录
- 同一预约重复触发违约不会重复写入
- 已签到预约不生成违约记录
- 学生主动取消预约不生成违约记录
- 管理员可查询违约记录
- 按 `user_id` 过滤违约记录
- 按 `student_no` 过滤违约记录
- 按 `room_id` 过滤违约记录
- 按时间范围过滤违约记录
- 无筛选条件时默认返回全部违约记录
- 管理端可查看指定用户的用户级违约次数统计
- 用户级违约次数统计按唯一 `reservation_id` 去重
- `get_user_penalty_status` 在未达到阈值时返回 `is_penalized=false`
- `get_user_penalty_status` 在达到阈值且惩罚期限未过时返回 `is_penalized=true`
- `get_user_penalty_status` 在达到阈值但惩罚期限已过时返回 `is_penalized=false`
- `get_user_penalty_status` 不重复统计同一 `reservation_id` 的同类型违约
- `get_user_penalty_status` 通过 `system_config` 公开 service 读取惩罚阈值、累计窗口和惩罚期限
- 管理员手动开启预约限制后，`get_user_penalty_status` 返回 `is_penalized=true`
- 管理员手动解除预约限制后，`get_user_penalty_status` 不再因手动限制返回 `is_penalized=true`
- 自动惩罚和手动限制同时存在时，统一状态必须表达两个来源
- `get_user_penalty_status` 查询过程不得修改 `Reservation`、`ViolationRecord`、`UserReservationBlock` 或用户数据
- 手动开启预约限制不得生成违约记录
- 手动解除预约限制不得物理删除历史限制记录
- 未认证访问违约接口失败
- 无权限访问违约接口失败
- 缺少 `violation.manual_blocks.write` 权限时，开启或解除手动预约限制失败

## 11. 完成标准

`violation` 模块第一版完成时，必须满足：

- `checkin` 可通过公开 service 触发超时未签到违约落账
- 同一预约不会生成重复违约记录
- 管理员可以查询违约记录
- 管理员可以查看指定用户的违约次数统计
- 管理员可以手动开启和解除指定用户的无期限预约限制
- 可基于已落账违约记录计算用户惩罚状态
- 可将自动违约惩罚与手动预约限制合并为统一只读预约限制状态
- 关键违约测试通过
