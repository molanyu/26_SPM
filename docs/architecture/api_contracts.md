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

- 查询指定自习室的座位及状态

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

### 4.3 reservation

#### `POST /student/reservations`

用途：

- 创建预约

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

#### `POST /admin/reservations/{reservation_id}/cancel`

用途：

- 管理员代取消预约

### 5.4 violation

#### `GET /admin/violations`

用途：

- 查询违约记录

输入参数：

- `user_id`
- `room_id`
- `date_from`
- `date_to`

#### `GET /admin/statistics/usage`

用途：

- 查询使用率和违约率统计

### 5.5 identity-rbac

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

- 停用角色（第一版删除语义）

#### `GET /admin/permissions`

用途：

- 查询权限点列表

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
- `department_id` 如提供，必须指向有效院系

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

### 5.6 system_config

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

- 生成每日动态签到码
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
