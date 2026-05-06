# Identity Module Spec

## 1. 任务定位

本文件定义 `identity` 模块的实现边界。

本模块是第一交付单元的一部分，负责提供以下基础能力：

- 用户信息
- 学生登录
- 管理员登录
- 单个用户创建
- 院系访问限制
- 角色权限
- 菜单权限判断

## 2. 实现范围

本次实现只包含以下内容：

- `Department`、`User`、`Role`、`Permission`、`UserRole`、`RolePermission` 的数据模型
- 学生登录接口
- 管理员登录接口
- 管理员退出接口
- 当前用户信息接口
- 单个用户创建接口
- 角色管理接口（创建、修改、停用）
- 用户角色分配接口
- 基础权限校验能力

本次实现不包含以下内容：

- 微信开放平台真实登录接入
- 单点登录
- 密码找回
- 多因素认证

### 2.1 冷启动 Bootstrap 规则

`identity` 模块必须支持空数据库首次进入可管理状态，规则固定如下：

- 系统必须支持空数据库首次进入可管理状态
- 必须幂等创建基础权限和管理员角色
- 必须提供首个管理员初始化机制
- 默认采用受控 bootstrap 方案，不允许每次启动重复写入
- 受控 bootstrap 只允许在显式启用时执行，未启用时应用启动只做建表和常规启动
- bootstrap 采用 `create-only` 语义：只创建缺失的基础权限、`system_admin` 角色和首个管理员账号
- 如果 `system_admin` 角色已存在，bootstrap 不得隐式修改其 `is_active`、权限绑定或其他状态
- 如果 bootstrap 管理员账号已存在，bootstrap 不得隐式修改其 `is_active`、角色绑定或其他状态
- 重新激活角色、重新激活管理员账号或修复既有授权，必须作为显式运维动作执行，不属于 bootstrap 行为
- 第一版演示环境默认不内置固定管理员账号；如需首次进入管理端，应通过 bootstrap 环境变量受控创建首个管理员
- bootstrap 创建完成后，首个管理员的实际浏览器登录路径固定为 `/admin/login`

## 3. 认证规则

认证方案固定如下：

### 3.1 学生端

- 学生使用 `student_no + password` 登录
- 登录成功后返回 `access_token`
- 学生端后续请求通过 `Authorization: Bearer <token>` 访问受保护接口

### 3.2 管理端

- 管理员使用 `email + password` 登录
- 登录成功后建立服务端会话
- 管理端页面与接口通过会话访问
- 管理员退出时清除会话
- 管理端浏览器页面使用 session cookie 访问
- 管理端浏览器默认登录入口为 `/admin/login`
- 管理端 HTML 页面与管理员 session 的关系固定为：页面只消费已建立的管理员 session，不单独维护第二套登录态
- `POST /admin/auth/login` 与浏览器表单登录共享同一套 session 创建逻辑

## 4. 权限规则

- 用户身份统一为 `User`
- 学生或管理员能力不通过用户类型字段判断
- 所有权限能力通过角色和权限点组合决定
- 用户创建与用户角色分配属于独立权限能力
- 用户创建需要独立权限 `identity.users.write`
- 管理端菜单显示由权限点决定
- 写操作必须做服务端权限校验

## 5. 数据模型范围

本模块使用以下实体：

- `Department`
- `User`
- `Role`
- `Permission`
- `UserRole`
- `RolePermission`

本模块必须保证以下数据规则：

- 学生登录标识使用 `student_no`
- 管理员登录标识使用 `email`
- 所有可登录用户必须存在 `password_hash`
- 创建用户时必须提供 `name`
- 创建学生账号时必须提供 `student_no`
- 创建学生账号时可选提供 `notification_email`，用于接收预约提醒、未签到提醒和自动取消通知
- 创建管理员账号时必须提供 `email`，该字段第一版可使用普通文本账号
- 学生登录仍只使用 `student_no`，不得因为填写 `notification_email` 而允许学生通过邮箱登录
- 第一版单个用户创建请求不同时提交 `student_no` 与管理员登录标识 `email`
- `notification_email` 不属于登录标识；如提供，可复用 `User.email` 存储，但语义固定为学生通知邮箱
- `notification_email` 如提供，必须是可用邮箱格式，且不得与既有 `User.email` 重复
- `department_id` 如提供，必须指向有效 `Department`
- 原始密码只允许在创建请求中出现，入库前必须转换为 `password_hash`
- 任何读取接口和用户创建成功响应都不得返回原始密码或 `password_hash`
- 用户可分配多个角色
- 角色可分配多个权限点
- 第一版“删除角色”通过受控停用实现，不做物理删除

## 6. 对外接口

本模块实现以下接口：

### 学生端

- `POST /student/auth/login`
- `GET /student/me`

### 管理端

- `GET /admin/login`
- `POST /admin/login`
- `POST /admin/logout`
- `POST /admin/auth/login`
- `POST /admin/auth/logout`
- `GET /admin/me`
- `POST /admin/users`
- `GET /admin/roles`
- `POST /admin/roles`
- `PUT /admin/roles/{role_id}`
- `POST /admin/roles/{role_id}/deactivate`
- `GET /admin/permissions`
- `POST /admin/users/{user_id}/roles`

## 7. 代码边界

目录固定如下：

```text
app/modules/identity/
  api/
  models/
  schemas/
  repositories/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责登录、鉴权、单个用户创建、角色分配、院系只读查询和菜单权限判断
- `repositories` 负责用户、角色、权限、院系的查询和写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `identity` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/identity/models/department.py
app/modules/identity/models/user.py
app/modules/identity/models/role.py
app/modules/identity/models/permission.py
app/modules/identity/models/user_role.py
app/modules/identity/models/role_permission.py

app/modules/identity/schemas/auth.py
app/modules/identity/schemas/user.py
app/modules/identity/schemas/role.py
app/modules/identity/schemas/permission.py

app/modules/identity/repositories/department_repository.py
app/modules/identity/repositories/user_repository.py
app/modules/identity/repositories/role_repository.py
app/modules/identity/repositories/permission_repository.py

app/modules/identity/services/auth_service.py
app/modules/identity/services/bootstrap_service.py
app/modules/identity/services/department_service.py
app/modules/identity/services/permission_service.py
app/modules/identity/services/menu_service.py

app/modules/identity/api/student_auth.py
app/modules/identity/api/admin_auth.py
app/modules/identity/api/admin_rbac.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立数据模型
2. 建立 schema
3. 建立 repository
4. 建立 auth service
5. 建立 permission service
6. 建立学生端登录接口
7. 建立管理端登录与退出接口
8. 建立单个用户创建接口
9. 建立角色管理与用户角色分配接口
10. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 学生登录成功
- 学生登录失败
- 管理员登录成功
- 管理员登录失败
- 浏览器登录页可访问
- bootstrap 创建的首个管理员可通过 `/admin/login` 完成浏览器登录
- 未认证访问受保护接口失败
- 无权限访问写接口失败
- 学生账号创建成功
- 学生账号创建成功时可保存可选通知邮箱
- 管理员账号创建成功
- 学生通知邮箱重复或格式非法时创建失败
- 重复学号或重复管理员登录标识创建失败
- 无效院系创建失败
- 用户创建成功响应不返回原始密码或 `password_hash`
- 角色创建成功
- 角色停用成功
- 用户角色分配成功
- 院系访问限制生效
- 菜单权限过滤生效
- 冷启动 bootstrap 可创建首个管理员并完成首次登录
- bootstrap 幂等执行不重复创建基础权限、管理员角色和首个管理员
- 已停用的 `system_admin` 角色在 bootstrap 再次执行后仍保持停用
- 已停用的 bootstrap 管理员账号在 bootstrap 再次执行后仍保持停用
- `IDENTITY_BOOTSTRAP_ENABLED=false` 时不发生 bootstrap 写入

## 11. 完成标准

`identity` 模块完成时，必须满足：

- 学生可以登录并获取访问令牌
- 管理员可以登录并建立会话
- 管理端浏览器可通过 `/admin/login` 复用管理员会话进入后台
- 当前用户信息接口可用
- 单个用户创建接口可用
- 角色管理接口可用
- 角色停用接口可用
- 用户角色分配接口可用
- 菜单权限可按权限点过滤
- 关键权限测试通过

## 12. Spec 增补（2026-04-21）

本文件已补入“单个用户创建”最小能力，目标范围如下：

- 支持系统管理员创建单个学生账号或管理员账号
- 支持写入姓名、登录标识、初始密码、启用状态、可选院系和学生可选通知邮箱
- 不扩展为用户列表、批量导入、密码回显或完整用户管理系统

截至本次文档增补时，代码侧仍应以当前工作区真实实现为准；新增能力需在后续实现与测试中补齐。

## 13. 实现回写（2026-04-15）

本轮已完成第一版实现，实际落地内容如下：

- 已建立最小 FastAPI 后端骨架与 `identity` 模块目录结构
- 已实现 `Department`、`User`、`Role`、`Permission`、`UserRole`、`RolePermission`
- 已实现学生 Bearer Token 登录与 `GET /student/me`
- 已实现管理员会话登录、退出与 `GET /admin/me`
- 已实现角色列表、角色创建、角色更新、权限点列表、用户角色分配
- 已实现基于权限点的服务端鉴权与菜单过滤
- 已实现受控 bootstrap，可幂等初始化基础权限、管理员角色与首个管理员
- 已提供院系访问限制基础校验 helper，供后续 `resource` 模块复用

本轮验证结论如下：

- `pytest -q -p no:cacheprovider` 通过，20 个 `identity` 相关测试全部通过
- 已覆盖学生登录成功/失败、管理员登录成功/失败、未认证访问失败、无权限写操作失败、角色创建/更新、用户角色分配、菜单权限过滤、院系访问限制 helper、冷启动 bootstrap、非法用户数据约束

本轮已知折中如下：

- 由于当前仓库尚无完整项目骨架，本轮同步创建了仅支撑 `identity` 的最小运行时骨架
- 管理员会话当前采用进程内服务端会话存储，适合作为第一版实现；后续若进入多实例部署，可替换为持久化会话存储
- 为便于本地开发与测试，默认数据库 URL 允许使用 SQLite；生产部署仍应按技术选型切换到 PostgreSQL

## 14. Spec 增补（2026-04-29）

本轮补入“院系最小管理”能力，目标是让管理端可自助准备院系基础数据，并保持 `Department` 仍归属 `identity` 模块。

范围固定如下：

- `DepartmentService` 提供公开 service 入口：列出全部院系、创建院系、启用院系、停用院系。
- 创建院系必须填写 `name`、`code` 和 `is_active`。
- `name` 与 `code` 必须保持唯一；重复名称或编码必须返回受控冲突错误，不允许 500。
- 院系停用通过 `is_active=false` 实现，不做物理删除。
- 创建用户和创建自习室仍只能读取启用院系。
- 院系管理写操作需要独立权限 `identity.departments.write`。
- 旧库必须通过受控 Alembic migration 补齐 `identity.departments.write` 权限定义；如果 `system_admin` 角色存在，只补缺失绑定，不修改角色启停状态或其他既有配置。

不包含以下内容：

- 院系列表之外的复杂组织架构。
- 院系树、批量导入、物理删除。
- 放宽 bootstrap 对已有角色和管理员账号的 create-only 边界。
