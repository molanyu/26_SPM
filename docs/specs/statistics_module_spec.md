# Statistics Module Spec

## 1. 任务定位

本文件定义 `G7 统计分析` 第一版实现的边界。

本阶段不新增新的一级业务模块，而是在既有模块边界内补充统计能力：

- 由 `violation` 负责管理端统计接口与统计编排
- 由 `resource` 提供统计所需的资源维度只读查询能力
- 基于既有 `Reservation`、`ViolationRecord`、`StudyRoom`、`Seat` 形成使用率与违约率统计

本阶段负责提供以下能力：

- 自习室使用率统计
- 座位使用率统计
- 违约率统计
- 管理端统一统计查询入口

## 2. 实现范围

本次实现只包含以下内容：

- `GET /admin/statistics/usage` 统计查询入口
- 按时间范围统计自习室使用率
- 按时间范围统计座位使用率
- 按时间范围统计违约率
- 统计结果所需的聚合查询与响应 schema
- 管理端可直接消费的统计结果结构

本次实现不包含以下内容：

- 管理端图表大盘页面
- 导出 Excel 或报表下载
- 实时占用看板
- 趋势预测与同比环比分析
- 资源开放时间与启停历史版本回放
- 多租户、多校区、多层级组织统计

### 2.1 第一版统计口径

第一版统计口径固定如下：

- 统计窗口基于请求给定的时间范围
- 使用率统计的预约分子只统计未取消的预约记录
- 违约率统计只统计 `NO_SHOW_TIMEOUT` 类型违约
- 违约率分母只统计在统计窗口内实际进入签到/超时判定链路的预约
- 第一版统计只提供运营分析口径，不提供审计级历史回放能力

说明：

- 若后续需要支持资源历史版本回放，应单独补充数据模型与顶层设计，不在本阶段展开
- 若接口需要落地为明确 query 参数，应同步回写 `api_contracts.md`

### 2.2 第一版统计维度

第一版至少输出以下维度：

- 总览统计
- 自习室维度统计
- 座位维度统计

其中：

- 总览统计至少包含总预约时长、总违约数、总体违约率
- 自习室维度统计至少包含 `room_id`、`room_name`、`usage_rate`
- 座位维度统计至少包含 `seat_id`、`seat_code`、`room_id`、`usage_rate`

## 3. 模块边界

- `G7 统计分析` 不是新的一级业务模块
- 管理端统计 HTTP 入口归 `violation` 模块负责
- 统计所需的资源维度数据只能通过 `resource` 的公开只读能力提供
- 统计实现不得直接跨模块调用对方 `repository`
- 统计实现不得新增跨模块写操作

跨模块协作规则固定如下：

- `violation` 可以基于自身统计 service 编排统计查询
- `violation` 如需房间、座位、开放时间、资源启用状态等维度信息，只能调用 `resource` 的公开 query service
- `resource` 只提供只读查询支持，不负责统计规则判定
- `reservation` 与 `violation` 的历史记录仍由各自模块维护，统计逻辑不得回写这些历史记录
- `admin_portal` 只消费统计接口，不承载统计计算逻辑

说明：

- 若进入正式编码阶段，应同步确认 `project_blueprint.md` 中对统计查询只读协作边界的表述已与本 spec 一致

## 4. 统计规则

统计规则固定如下：

### 4.1 使用率统计

- 自习室使用率按统计窗口内预约占用时长与可预约总时长的比例计算
- 座位使用率按统计窗口内单座位预约占用时长与单座位可预约总时长的比例计算
- 取消预约不计入使用率分子
- 第一版使用率统计不回放历史资源结构，默认基于当前有效资源配置计算可预约时长

### 4.2 违约率统计

- 违约率只统计 `NO_SHOW_TIMEOUT` 违约
- 同一预约最多只计入一次违约
- 违约率查询必须基于已经落账的违约记录，不允许从临时状态推导未落账违约

### 4.3 时间范围规则

- 统计查询必须显式提供时间范围
- 时间范围非法时必须返回参数错误
- 聚合、筛选与比率计算必须优先在数据库查询层完成

### 4.4 权限规则

- 统计查询只允许管理员访问
- 学生端不暴露统计接口
- 统计接口不提供写能力

## 5. 数据模型范围

本阶段不新增持久化业务实体。

本阶段使用以下既有实体：

- `StudyRoom`
- `Seat`
- `Reservation`
- `ViolationRecord`

本阶段必须遵守以下数据规则：

- 统计必须基于真实预约与违约记录计算
- 不允许为第一版统计新增冗余结果表
- 如需额外返回统计响应结构，应使用 schema 定义，不新增数据库模型

## 6. 对外接口与公开 service

本阶段实现以下入口：

### 管理端接口

- `GET /admin/statistics/usage`

### 公开 service

- `get_usage_statistics(...)`
- `get_room_statistics_context(...)`

说明：

- `get_usage_statistics(...)` 由 `violation` 提供，用于编排总体统计、自习室统计与座位统计
- `get_room_statistics_context(...)` 由 `resource` 提供，只返回统计所需的只读资源上下文
- 公开 service 命名可调整，但职责边界不可改变

## 7. 代码边界

本阶段建议目录如下：

```text
app/modules/violation/
  api/
  schemas/
  repositories/
  services/

app/modules/resource/
  services/
```

边界规则如下：

- `violation.api` 负责统计接口接入
- `violation.schemas` 定义统计请求与响应结构
- `violation.repositories` 负责统计聚合查询
- `violation.services` 负责统计口径编排与结果组装
- `resource.services` 负责提供资源统计上下文只读能力
- 不允许把统计逻辑放进 `admin_portal`

## 8. 文件级实现清单

本阶段实现至少包含以下文件或同等职责文件：

```text
app/modules/violation/schemas/statistics.py

app/modules/violation/repositories/statistics_repository.py

app/modules/violation/services/statistics_service.py

app/modules/violation/api/admin_statistics.py

app/modules/resource/services/statistics_query_service.py

tests/violation/test_admin_statistics.py
```

说明：

- 如项目更倾向于把统计接口并入既有 `admin_violation.py`，可复用该文件，但必须保持职责清晰

## 9. 实现顺序

实现顺序固定如下：

1. 明确统计口径与响应 schema
2. 建立资源统计上下文只读查询能力
3. 建立统计聚合 repository
4. 建立统计 service
5. 建立管理端统计接口
6. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本阶段至少覆盖以下测试：

- 管理员可查询总览统计
- 管理员可查询自习室使用率统计
- 管理员可查询座位使用率统计
- `NO_SHOW_TIMEOUT` 违约可正确计入违约率
- 取消预约不会计入使用率
- 非法时间范围返回参数错误
- 未认证访问统计接口失败
- 无权限访问统计接口失败

## 11. 完成标准

`G7 统计分析` 第一版完成时，必须满足：

- 管理员可以通过统一接口查询使用率与违约率
- 自习室与座位维度统计可直接返回给管理端消费
- 统计计算主要在数据库查询层完成
- 统计实现不破坏既有模块边界
- 关键统计测试通过
