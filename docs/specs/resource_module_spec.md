# Resource Module Spec

## 1. 任务定位

本文件定义 `resource` 模块的实现边界。

本模块是第二交付单元的一部分，负责提供以下基础能力：

- 自习室管理
- 座位管理
- 自习室可见性过滤
- 开放时间管理
- 座位属性筛选

## 2. 实现范围

本次实现只包含以下内容：

- `StudyRoom`、`Seat` 的数据模型
- 学生端自习室列表查询
- 学生端指定自习室座位列表查询
- 按院系和公共范围过滤自习室可见性
- 按靠窗、固定插座、移动导轨插座筛选座位
- 管理员端自习室创建、修改、注销
- 管理员端座位创建、修改、注销

本次实现不包含以下内容：

- 预约创建、预约取消、预约冲突判定
- 预约占用统计
- 签到、违约、提醒
- 自然语言查询
- 前端座位地图渲染细节

### 2.1 资源可见性规则

`resource` 模块必须固定遵守以下规则：

- 公共自习室对所有学生可见
- 院系专属自习室只对同院系学生可见
- 已注销或未启用的自习室对学生不可见
- 已注销或未启用的座位对学生不可见
- 学生端自习室查询必须基于当前登录学生身份过滤

### 2.2 开放时间规则

- 自习室必须维护 `open_time` 和 `close_time`
- 学生端只返回当前仍可用于预约链路的自习室与座位基础信息
- `resource` 只负责开放时间数据的维护与查询
- 是否允许具体预约时间段，属于 `reservation` 和 `system_config` 的职责，不属于 `resource`

### 2.3 座位状态边界

- `GET /student/rooms/{room_id}/seats` 必须返回 `status` 字段
- 在 `G2` 阶段，`resource` 只负责返回资源侧状态
- 资源侧状态只由以下因素决定：
  - 自习室是否可见
  - 自习室是否启用
  - 座位是否启用
  - 查询参数是否合法
- 预约冲突、已预约、已占用等预约链路状态不属于 `resource` 的决策范围
- `resource` 不得依赖 `reservation` 模块去计算座位占用状态

## 3. 资源规则

资源规则固定如下：

### 3.1 自习室

- 自习室可以是公共自习室或院系专属自习室
- `department_id` 为空表示公共自习室
- `is_department_only=true` 表示该自习室只允许对应院系学生访问
- 自习室注销采用 `is_active=false`
- 自习室注销后不得再出现在学生端可见列表中

### 3.2 座位

- 座位必须归属于一个自习室
- 座位注销采用 `is_active=false`
- 同一自习室内 `seat_code` 必须唯一
- 座位属性至少包含：
  - `is_window_side`
  - `has_power_socket`
  - `has_track_socket`

## 4. 模块边界

- `resource` 可以依赖 `identity` 的公开 service 获取当前学生身份和院系信息
- `resource` 不依赖 `reservation`
- `resource` 不依赖 `checkin`
- `resource` 不依赖 `violation`
- `resource` 不依赖 `notification`
- `resource` 不直接读取或写入其他模块的 repository

跨模块协作规则固定如下：

- 学生院系访问限制通过 `identity` 公开 service 或依赖注入结果完成
- 预约时间段是否合法不在 `resource` 内决策
- 座位是否存在预约冲突不在 `resource` 内决策

## 5. 数据模型范围

本模块使用以下实体：

- `StudyRoom`
- `Seat`

本模块必须保证以下数据规则：

- `StudyRoom.name` 必须可读且可用于列表展示
- `StudyRoom.location` 必须可读且可用于列表展示
- `StudyRoom.open_time` 和 `close_time` 必须存在
- `Seat.seat_code` 在同一 `room_id` 下唯一
- `Seat.room_id` 必须指向有效自习室

## 6. 对外接口

本模块实现以下接口：

### 学生端

- `GET /student/rooms`
- `GET /student/rooms/{room_id}/seats`

### 管理端

- `GET /admin/rooms`
- `POST /admin/rooms`
- `PUT /admin/rooms/{room_id}`
- `POST /admin/rooms/{room_id}/deactivate`
- `GET /admin/seats`
- `POST /admin/seats`
- `PUT /admin/seats/{seat_id}`
- `POST /admin/seats/{seat_id}/deactivate`

## 7. 代码边界

目录固定如下：

```text
app/modules/resource/
  api/
  models/
  schemas/
  repositories/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责可见性过滤、资源规则和管理端用例编排
- `repositories` 负责自习室和座位的查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `resource` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/resource/models/study_room.py
app/modules/resource/models/seat.py

app/modules/resource/schemas/room.py
app/modules/resource/schemas/seat.py

app/modules/resource/repositories/room_repository.py
app/modules/resource/repositories/seat_repository.py

app/modules/resource/services/room_service.py
app/modules/resource/services/seat_service.py
app/modules/resource/services/visibility_service.py

app/modules/resource/api/student_resource.py
app/modules/resource/api/admin_resource.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `StudyRoom`、`Seat` 数据模型
2. 建立 room 和 seat 的 schema
3. 建立 room 和 seat 的 repository
4. 建立可见性与属性筛选 service
5. 建立学生端查询接口
6. 建立管理端 room CRUD 与 deactivate 接口
7. 建立管理端 seat CRUD 与 deactivate 接口
8. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 学生只能看到自己有权限访问的自习室
- 公共自习室对所有学生可见
- 院系专属自习室对非本院系学生不可见
- 学生可查询指定自习室座位列表
- 学生可按靠窗筛选座位
- 学生可按固定插座筛选座位
- 学生可按移动导轨插座筛选座位
- 已注销座位不会返回给学生端
- 管理员可创建自习室
- 管理员可修改自习室
- 管理员可注销自习室
- 管理员可创建座位
- 管理员可修改座位
- 管理员可注销座位
- 同一自习室内重复 `seat_code` 会被拒绝

## 11. 完成标准

`resource` 模块完成时，必须满足：

- 学生可以查询自己可见的自习室列表
- 学生可以查询指定自习室的座位列表
- 座位属性筛选可用
- 自习室管理接口可用
- 座位管理接口可用
- 关键资源测试通过
