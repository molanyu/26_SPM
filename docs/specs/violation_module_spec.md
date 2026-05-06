# Violation Module Spec

## 1. 任务定位

本文件定义 `violation` 模块第一版实现的边界。

本模块在当前阶段负责提供以下基础能力：

- 违约记录落账
- 违约记录查询
- 对 `checkin` 提供违约落账公开 service

## 2. 实现范围

本次实现只包含以下内容：

- `ViolationRecord` 数据模型
- 超时未签到违约记录生成
- 管理端违约记录查询接口
- 对 `checkin` 暴露的违约落账 service

本次实现不包含以下内容：

- 违约率统计
- 自习室/座位使用率统计
- 提醒通知
- 管理端统计大盘
- 复杂违约类型体系

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

## 3. 模块边界

- `violation` 可以依赖 `reservation`
- `violation` 不依赖 `resource`
- `violation` 不依赖 `checkin`
- `violation` 不依赖 `notification`
- `violation` 不依赖 `system_config`

跨模块协作规则固定如下：

- `checkin` 只能通过 `violation` 的公开 service 触发违约落账
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
- 写接口不对外暴露 HTTP 入口
- 违约落账只能由内部 service 触发

## 5. 数据模型范围

本模块使用以下实体：

- `ViolationRecord`

本模块必须保证以下数据规则：

- `user_id` 必须指向有效用户
- `reservation_id` 必须指向有效预约
- `violation_type` 必须使用已定义枚举
- `occurred_at` 必须记录违约发生时间
- 同一 `reservation_id + violation_type` 组合必须唯一

## 6. 对外接口与公开 service

本模块第一版实现以下入口：

### 管理端接口

- `GET /admin/violations`

### 公开 service

- `record_timeout_violation(reservation_id)`

说明：

- 第一版不实现统计接口
- 第一版不实现对外 HTTP 写接口

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
- `services` 负责违约落账、幂等校验、查询编排
- `repositories` 负责违约记录查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `violation` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/violation/models/violation_record.py

app/modules/violation/schemas/violation.py

app/modules/violation/repositories/violation_repository.py

app/modules/violation/services/violation_service.py
app/modules/violation/services/query_service.py

app/modules/violation/api/admin_violation.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `ViolationRecord` 数据模型
2. 建立 violation schema
3. 建立 violation repository
4. 建立违约落账与查询 service
5. 建立管理端查询接口
6. 建立基础测试

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
- 未认证访问违约接口失败
- 无权限访问违约接口失败

## 11. 完成标准

`violation` 模块第一版完成时，必须满足：

- `checkin` 可通过公开 service 触发超时未签到违约落账
- 同一预约不会生成重复违约记录
- 管理员可以查询违约记录
- 关键违约测试通过
