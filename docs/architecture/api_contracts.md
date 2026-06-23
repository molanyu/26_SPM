# 接口契约

## 1. 文档定位

本文件定义系统对外接口边界。

本文件只回答以下问题：

- 暴露哪些接口
- 每个接口属于哪个模块
- 每个接口的用途是什么
- 每个接口需要什么权限
- 每个接口输入输出的核心结构是什么

本文件不定义数据库表结构，不定义页面布局，不定义具体代码实现。

## 2. 接口设计原则

- 接口按业务模块组织
- 学生端接口与管理端接口分开
- 一个接口只处理一个明确动作
- 写操作必须显式校验权限和状态
- 查询接口优先支持筛选、分页、排序
- 返回结构保持稳定，不混入页面展示逻辑

## 3. 接口分组

接口统一分为三类：

- 学生端接口：前缀 `/student`
- 管理端接口：前缀 `/admin`
- 系统任务接口：不对外暴露，仅供内部任务调用

## 4. 学生端接口

### 4.1 identity

#### `POST /student/auth/login`

用途：

- 学生登录并获取访问令牌

输入核心字段：

- `student_no`
- `password`

返回核心字段：

- `access_token`
- `token_type`
- `user`

#### `GET /student/me`

用途：

- 获取当前学生信息

返回核心字段：

- `id`
- `name`
- `student_no`
- `department`

### 4.2 resource

#### `GET /student/rooms`

用途：

- 查询当前学生可见的自习室列表

输入参数：

- `page`
- `page_size`

返回核心字段：

- `id`
- `name`
- `location`
- `open_time`
- `close_time`
- `department_scope`

#### `GET /student/rooms/{room_id}/seats`

用途：

- 查询指定自习室的座位及资源侧状态

输入参数：

- `date`
- `start_time`
- `end_time`
- `is_window_side`
- `has_power_socket`

返回核心字段：

- `seat_id`
- `seat_code`
- `seat_label`
- `status`
- `is_window_side`
- `has_power_socket`
- `has_track_socket`

说明：

- `status` 只表示资源侧状态，不表示指定时段内是否已有预约占用
- 指定时段最终可用状态由 `reservation` 的座位可用状态查询契约提供

### 4.3 reservation

#### `POST /student/reservations`

用途：

- 创建预约

规则：

- `start_time` 必须晚于当前时间
- `start_time` 和 `end_time` 必须按 30 分钟粒度提交，分钟只允许为 `00` 或 `30`，秒和微秒必须为 `0`

输入核心字段：

- `seat_id`
- `start_time`
- `end_time`

返回核心字段：

- `reservation_id`
- `status`
- `seat_id`
- `room_id`
- `start_time`
- `end_time`

#### `GET /student/rooms/{room_id}/seat-availability`

用途：

- 查询指定自习室在指定时段内的座位最终可用状态

规则：

- 该接口由 `reservation` 模块编排
- 资源基础信息、可见性、开放时间和座位属性由 `resource` 公开 service 提供
- 预约占用状态由 `reservation` 基于 `BOOKED` / `CHECKED_IN` 且时间区间重叠的预约记录计算
- `CANCELLED` 和 `EXPIRED` 预约不得计入占用
- 查询、筛选和重叠判断必须在数据库层完成

输入参数：

- `date`
- `start_time`
- `end_time`
- `is_window_side`
- `has_power_socket`
- `has_track_socket`

返回核心字段：

- `seat_id`
- `seat_code`
- `seat_label`
- `status`
- `is_window_side`
- `has_power_socket`
- `has_track_socket`

说明：

- `status` 表示指定时段最终状态，至少包含 `AVAILABLE` 和 `OCCUPIED`
- 该接口不改变预约或资源状态

#### `GET /student/reservations/current`

用途：

- 查询当前有效预约

输入参数：

- 无

返回核心字段：

- `items`
- `total`

说明：

- `items` 内元素字段与预约写接口返回的核心预约字段保持一致
- 当前有效预约只包含未结束的 `BOOKED` / `CHECKED_IN` 预约

#### `GET /student/reservations/history`

用途：

- 查询历史预约记录

输入参数：

- `page`
- `page_size`

#### `POST /student/reservations/{reservation_id}/cancel`

用途：

- 学生主动取消预约

输入核心字段：

- `reason`

### 4.4 checkin

#### `POST /student/checkins/code`

用途：

- 通过动态码签到

输入核心字段：

- `reservation_id`
- `code`

#### `POST /student/checkins/qrcode`

用途：

- 通过二维码签到

输入核心字段：

- `reservation_id`
- `token`

### 4.5 assistant

#### `POST /student/assistant/query`

用途：

- 处理自然语言查询

输入核心字段：

- `message`

返回核心字段：

- `intent`
- `result_type`
- `result`

## 5. 管理端接口

### 5.1 identity

#### `GET /admin/login`

用途：

- 返回管理端浏览器登录页

说明：

- 该入口仅用于服务端渲染 HTML 登录页
- 已登录管理员再次访问时，可直接跳转到 `/admin` 或请求中的受保护目标页

#### `POST /admin/login`

用途：

- 处理管理端浏览器表单登录并建立会话

输入核心字段：

- `email`
- `password`
- `next`

返回规则：

- 登录成功后建立 session cookie，并重定向到 `next` 或 `/admin`
- 登录失败时返回受控 HTML 登录页与错误信息

#### `POST /admin/auth/login`

用途：

- 管理员登录并建立会话

说明：

- 该入口保留为 JSON/API 场景
- 浏览器表单场景优先使用 `POST /admin/login`
- 两者底层复用同一套管理员 session 创建逻辑

输入核心字段：

- `email`
- `password`

#### `POST /admin/logout`

用途：

- 处理管理端浏览器退出并清除会话

返回规则：

- 退出后重定向到 `/admin/login`

#### `POST /admin/auth/logout`

用途：

- 管理员退出登录并清除会话

#### `GET /admin/me`

用途：

- 获取当前管理员信息与菜单权限

返回核心字段：

- `id`
- `name`
- `roles`
- `permissions`
- `menus`

### 5.2 resource

#### `GET /admin/rooms`

用途：

- 查询自习室列表

#### `POST /admin/rooms`

用途：

- 创建自习室

#### `PUT /admin/rooms/{room_id}`

用途：

- 修改自习室

#### `POST /admin/rooms/{room_id}/deactivate`

用途：

- 注销自习室

#### `GET /admin/seats`

用途：

- 查询座位列表

#### `POST /admin/seats`

用途：

- 创建座位

#### `PUT /admin/seats/{seat_id}`

用途：

- 修改座位

#### `POST /admin/seats/{seat_id}/deactivate`

用途：

- 注销座位

### 5.3 reservation

#### `GET /admin/reservations`

用途：

- 查询预约记录

输入参数：

- `user_id`
- `room_id`
- `seat_id`
- `status`
- `date_from`
- `date_to`

#### `GET /admin/reservations`

用途：

- 查询预约记录

输入参数：

- `user_id`
- `room_id`
- `seat_id`
- `status`
- `date_from`
- `date_to`
- `page`
- `page_size`

#### `POST /admin/reservations`

用途：

- 管理员代预约

规则：

- 与学生创建预约使用同一套预约时间规则
- `start_time` 必须晚于当前时间
- `start_time` 和 `end_time` 必须按 30 分钟粒度提交

#### `POST /admin/reservations/{reservation_id}/cancel`

用途：

- 管理员代取消预约

### 5.4 violation

#### `GET /admin/violations`

用途：

- 查询违约记录
- 在指定单个用户时返回用户级违约次数统计和统一预约限制状态

输入参数：

- `user_id`
- `student_no`
- `room_id`
- `date_from`
- `date_to`
- `page`
- `page_size`

返回核心字段：

- `items`
- `total`
- `page`
- `page_size`
- `user_summary`

`user_summary` 在请求能唯一定位单个用户时返回，核心字段：

- `user_id`
- `student_no`
- `violation_count`
- `is_penalized`
- `restriction_source`
- `penalty_start`
- `penalty_end`
- `manual_block_id`
- `manual_block_reason`
- `manual_block_started_at`

说明：

- 所有筛选条件均可选
- 无筛选条件时默认分页返回全部违约记录
- 管理端 HTML 页面发生参数错误时必须渲染统一页面错误，不返回裸 JSON
- 用户级违约次数只统计已经落账的 `NO_SHOW_TIMEOUT` 记录，并按唯一 `reservation_id` 去重
- 用户级违约次数统计不等同于统计大盘，不提供排行、趋势或复杂维度分析
- `is_penalized` 是 `violation` 汇总后的统一预约限制状态，包含自动违约惩罚和管理员手动预约限制

#### `POST /admin/violations/users/{user_id}/manual-block`

用途：

- 管理员手动开启指定用户的预约限制

权限：

- `violation.manual_blocks.write`
- 服务端必须校验该权限，不能只依赖页面隐藏按钮

输入核心字段：

- `reason`

返回核心字段：

- `success`
- `message`
- `data`

`data` 核心字段：

- `user_id`
- `manual_block_id`
- `is_penalized`
- `restriction_source`
- `manual_block_reason`
- `manual_block_started_at`

说明：

- 第一版手动预约限制为无期限限制，开启后持续生效，直到管理员解除
- 同一用户同一时间最多只能存在一条有效手动预约限制
- 重复开启已有效限制时不得生成多个有效限制，必须返回受控结果
- 手动开启限制不得新增违约记录，不得修改预约记录

#### `POST /admin/violations/users/{user_id}/manual-block/release`

用途：

- 管理员解除指定用户当前有效的手动预约限制

权限：

- `violation.manual_blocks.write`
- 服务端必须校验该权限，不能只依赖页面隐藏按钮

返回核心字段：

- `success`
- `message`
- `data`

`data` 核心字段：

- `user_id`
- `manual_block_id`
- `is_penalized`
- `restriction_source`
- `released_at`

说明：

- 解除只影响手动预约限制，不清除违约记录，也不改变自动违约累计惩罚
- 如果用户仍处于自动违约惩罚期，解除手动限制后 `is_penalized` 仍可为 `true`
- 目标用户不存在或不存在有效手动预约限制时，必须返回受控业务错误
- 解除时必须保留历史手动限制记录，不得物理删除

#### `GET /admin/statistics/usage`

用途：

- 查询使用率和违约率统计

### 5.5 checkin

#### `GET /admin/checkins`

用途：

- 查看指定自习室当前动态签到码状态
- 查看签到记录

说明：

- 管理端 HTML 请求返回动态签到码与签到记录页面
- 非 HTML/API 请求返回当前动态码状态与签到记录数据
- 不提供人工代签到、补签或批量操作
- 不提供生成签到码动作；当前动态码由服务端按自习室和 5 分钟时间片自动派生

### 5.6 notification

#### `GET /admin/notifications`

用途：

- 查看通知日志
- 查看当前通知通道配置

说明：

- 管理端 HTML 请求返回通知日志查询页面
- 非 HTML/API 请求返回通知日志数据

#### 通知后台调度

用途：

- 由应用后台调度器自动触发预约前提醒、未签到提醒和超时未签到释放通知

说明：

- 管理端不提供手动触发通知任务的页面或表单入口
- 自动化测试和验收可使用内部 scheduler `tick/run_once` 或 injected now 模拟时间推进
- 不提供复杂调度、SMTP 配置管理或外部 smoke 自动化

### 5.7 identity-rbac

#### `GET /admin/roles`

用途：

- 查询角色列表

#### `POST /admin/roles`

用途：

- 创建角色

#### `PUT /admin/roles/{role_id}`

用途：

- 修改角色

#### `POST /admin/roles/{role_id}/deactivate`

用途：

- 停用角色

说明：

- 停用角色用于禁用或下线角色，不做物理删除

#### `DELETE /admin/roles/{role_id}`

用途：

- 删除角色

权限：

- `identity.roles.write`

说明：

- 只允许删除未分配给任何用户、非系统保留角色的角色
- 第一版系统保留角色固定按 `Role.code == "system_admin"` 判定，不新增数据字段；`system_admin` 即使未分配用户也不得删除
- 删除时清理该角色的 `role_permissions`
- 不删除 `users`，不删除 `permissions`
- 如果角色存在 `user_roles` 分配，必须返回受控状态错误，并提示先解除分配或停用角色

#### `GET /admin/permissions`

用途：

- 查询权限点列表

#### `GET /admin/departments`

用途：

- 查询院系列表

权限：

- `identity.departments.write`

说明：

- 管理端 HTML 请求可返回院系管理页面
- 非 HTML/API 请求返回院系列表数据
- 列表包含启用和停用院系；创建用户和创建自习室的下拉选项仍只使用启用院系

返回核心字段：

- `id`
- `name`
- `code`
- `is_active`

#### `POST /admin/departments`

用途：

- 创建院系

权限：

- `identity.departments.write`

说明：

- 仅支持单个创建
- 不支持批量导入、删除、院系树或复杂组织架构
- 重复院系名称或编码必须返回受控冲突错误

输入核心字段：

- `name`
- `code`
- `is_active`

返回核心字段：

- `id`
- `name`
- `code`
- `is_active`

#### `POST /admin/departments/{department_id}/activate`

用途：

- 启用院系

权限：

- `identity.departments.write`

说明：

- 启用后可出现在创建用户和院系专属自习室的院系下拉选项中

#### `POST /admin/departments/{department_id}/deactivate`

用途：

- 停用院系

权限：

- `identity.departments.write`

说明：

- 停用后不得出现在创建用户和创建自习室的可选院系列表中
- 停用不做物理删除，不影响历史用户、自习室和预约记录

#### `POST /admin/users`

用途：

- 创建单个学生或管理员账号

说明：

- 仅支持单个创建
- 不支持批量导入
- 不返回原始密码或 `password_hash`

输入核心字段：

- `account_type`
- `name`
- `student_no` 或 `email`
- `notification_email`
- `password`
- `department_id`
- `is_active`

输入规则：

- 学生账号提交 `student_no`
- 学生账号可选提交 `notification_email`，用于接收通知，不作为登录标识
- 管理员账号提交 `email`
- 第一版为保持账号语义清晰，同一创建请求不同时提交 `student_no` 与管理员登录标识 `email`
- `email` 字段第一版仅作为管理员登录标识，不强制邮件格式，可使用普通文本账号
- `notification_email` 如提供，必须是可用邮箱格式，且不得与既有 `User.email` 重复
- `department_id` 如提供，必须指向有效且启用的院系

返回核心字段：

- `id`
- `name`
- `student_no`
- `email`
- `notification_email`
- `department`
- `is_active`

#### `POST /admin/users/{user_id}/roles`

用途：

- 为用户分配角色

输入核心字段：

- `role_ids`

### 5.8 system_config

#### `GET /admin/system-configs`

用途：

- 查询系统参数

#### `PUT /admin/system-configs/{config_key}`

用途：

- 更新系统参数

输入核心字段：

- `config_value`

## 6. 内部任务接口

内部任务不对外暴露 HTTP 接口，通过任务调度直接调用 service。

内部任务固定包括：

- 动态签到码由 checkin service 按需派生，不设置每日生成任务作为当前码来源
- 发送预约前提醒
- 发送未签到提醒
- 执行超时释放
- 生成违约记录

## 7. 权限规则

- 学生端接口默认要求学生身份
- 管理端接口默认要求管理员身份
- 角色和权限由 `identity` 模块统一判定
- 菜单可见性和操作权限必须同时受权限控制
- 写接口必须做服务端权限校验，不能只依赖前端隐藏按钮
- 院系管理写操作需要 `identity.departments.write` 权限，菜单入口也必须按该权限裁剪
- 学生端使用 Bearer Token 访问受保护接口
- 管理端使用服务端会话访问受保护页面和接口
- 未登录访问受保护管理端 HTML 页面时，应重定向到 `/admin/login`
- 未登录访问纯管理端接口时，应继续返回受控 JSON 未认证错误
- 登录成功后的浏览器默认跳转目标为 `/admin`；如请求中显式提供安全的 `next` 页面路径，则优先跳转到该路径
- 浏览器退出后默认跳转到 `/admin/login`

## 8. 错误返回规则

错误响应统一包含：

- `code`
- `message`
- `details`

列表查询统一返回：

- `items`
- `total`
- `page`
- `page_size`

写接口成功响应统一返回：

- `success`
- `message`
- `data`

必须覆盖以下错误类型：

- 参数错误
- 未认证
- 无权限
- 资源不存在
- 状态不合法
- 时间冲突
- 签到码无效
- 系统配置限制不满足

## 9. 变更规则

新增接口或修改接口时，必须先确认：

- 属于哪个模块
- 是否破坏现有模块边界
- 是否影响已有权限规则
- 是否影响已有状态流转

确认后先修改本文件，再修改代码。
