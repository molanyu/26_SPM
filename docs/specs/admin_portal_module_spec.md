# Admin Portal Module Spec

## 1. 任务定位

本文件定义 `admin_portal` 模块第一版实现的边界。

本模块在当前阶段负责提供以下能力：

- 管理端页面壳
- 管理端菜单渲染
- 管理端表单与列表页
- 用户创建页
- 已有业务模块能力的界面适配
- 管理端统一布局与主题切换

## 2. 实现范围

本次实现只包含以下内容：

- 管理端浏览器登录页与登录跳转闭环
- 管理端基础布局页
- 管理端共享主题与亮暗主题切换
- 基于权限的菜单渲染
- 用户创建页面
- 院系管理页面
- 自习室管理页面
- 座位管理页面
- 系统参数管理页面
- 预约记录查询页面
- 管理员代预约与代取消页面
- 动态签到码与签到记录页面
- 统计查询页面
- 违约记录查询页面
- 通知日志与任务触发页面
- 角色管理与用户角色分配页面

本次实现不包含以下内容：

- 核心业务规则判定
- 直接数据库读写
- 复杂图表统计大盘页面
- 复杂通知运营页面
- 助手管理页面
- 用户列表页
- 批量导入用户
- 当前密码显示或密码回显
- 复杂前端状态管理框架

### 2.1 页面范围

第一版固定只交付以下页面：

- 管理端登录页
- 登录后基础管理端首页
- 菜单导航与基础布局
- 用户创建页
- 院系管理页
- `identity` 相关管理页面
- `resource` 相关管理页面
- `system_config` 相关管理页面
- `reservation` 查询与代理操作页面
- `checkin` 动态签到码与签到记录页面
- `statistics` 查询页面
- `violation` 记录查询页面
- `notification` 日志与任务触发页面

### 2.2 菜单规则

- 管理端菜单只能基于 `identity` 返回的菜单权限渲染
- 前端隐藏菜单不是权限校验的替代
- 即使菜单隐藏，服务端接口仍必须保留权限校验
- 院系管理入口由 `identity.departments.write` 权限控制，首页快捷入口和侧边栏菜单必须与服务端权限一致

### 2.3 浏览器登录闭环规则

- 第一版管理端必须提供浏览器登录页 `GET /admin/login`
- 管理端浏览器默认从 `/admin/login` 进入
- 未登录访问受保护管理端 HTML 页面时，必须重定向到 `/admin/login`
- 重定向到登录页时应保留原始目标页，登录成功后优先跳回原目标页；未提供目标页时跳转到 `/admin`
- 管理员退出后必须跳转回 `/admin/login`
- 管理端浏览器登录只复用现有 `identity` 管理员 session 机制，不引入新的认证体系
- 管理端 HTML 页面与表单流必须以 session cookie 作为登录态载体
- 对纯接口请求，不得因为浏览器登录页闭环而破坏原有 JSON 错误边界

## 3. 界面规则

界面规则固定如下：

### 3.1 布局规则

- 使用统一后台布局
- 管理端视觉 token、主题变量和高频控件样式必须集中维护在单一共享来源
- 页面模板不得各自维护一套独立整页主样式
- 列表页优先承担浏览、筛选和跳转，不在表格行内直接承载高密度复杂编辑器
- 页面结构保持扁平，不引入复杂组件树
- 页面只负责展示、收集表单输入和调用对应 service

### 3.2 主题规则

- 管理端必须支持 `light` 和 `dark` 两种主题
- `light` 主题使用浅色、柔和的莫兰迪色系
- `dark` 主题可沿用当前深色方向，但必须保证可读性、层级和操作反馈清晰
- 主题切换结果在刷新后必须保持
- 两种主题下的布局结构、组件语义和交互入口必须保持一致

### 3.3 表单规则

- 表单字段必须与对应模块公开 schema 对齐
- 表单提交失败时展示服务端返回的错误
- 页面不得自行复制核心业务规则
- 用户创建页只采集初始密码，不展示当前密码，也不回显 `password_hash`
- 用户创建页在选择学生账号时，应显示可选“通知邮箱”字段；该字段用于接收通知，不作为学生登录方式
- 用户创建页在选择管理员账号时，仍显示管理员登录标识字段；不得把管理员登录标识与学生通知邮箱混为同一说明
- 开关、勾选、属性选择、筛选条等高频控件必须复用统一样式，不得每页各自定义一套视觉形式

### 3.4 查询规则

- 列表页的查询参数必须透传给对应模块公开 service
- 分页、筛选、排序由后端 service 决定
- 页面不得在浏览器侧重写复杂筛选逻辑

## 4. 模块边界

- `admin_portal` 可以依赖各业务模块的公开 service
- `admin_portal` 不直接调用任何模块的 repository
- `admin_portal` 不直接修改任何业务 model 状态
- `admin_portal` 不承载核心业务规则

跨模块协作规则固定如下：

- 登录态与菜单权限由 `identity` 提供
- 院系管理页面调用 `identity` 公开 `DepartmentService`
- 自习室、座位页面调用 `resource` 公开 service
- 系统参数页面调用 `system_config` 公开 service
- 代理预约与代取消页面调用 `reservation` 公开 service
- 违约记录页面调用 `violation` 公开 service
- 浏览器登录页与跳转逻辑只负责页面闭环，不改变 `identity` 的 session 生成与校验规则

## 5. 数据模型范围

本模块第一版不新增业务数据模型。

本模块只消费其他业务模块已经存在的公开数据结构。

## 6. 对外入口

本模块第一版实现以下页面入口：

- `/admin/login`
- `/admin`
- `/admin/users/new`
- `/admin/departments`
- `/admin/roles`
- `/admin/users/{user_id}/roles`
- `/admin/rooms`
- `/admin/seats`
- `/admin/system-configs`
- `/admin/reservations/records`
- `/admin/reservations/actions`
- `/admin/checkins`
- `/admin/statistics`
- `/admin/violations`
- `/admin/notifications`

说明：

- 这些页面由服务端渲染
- `/admin/departments` 用于查看、新增、启用和停用院系，不承担院系树、批量导入、删除或复杂组织架构
- 页面提交动作最终调用对应模块的公开 service 或现有接口
- `/admin/login` 是浏览器登录页入口
- 登录成功后默认跳转 `/admin`
- `/admin/users/new` 用于创建单个学生或管理员账号，不承担用户列表与批量导入
- `/admin/checkins` 用于查看指定自习室当前动态签到码状态、有效至时间和签到记录，不提供生成签到码、人工代签到或批量补签
- `/admin/notifications` 用于查看通知日志和手动触发已有内部通知任务，不承担复杂调度或 SMTP 配置管理
- `POST /admin/login` 与 `POST /admin/logout` 作为浏览器表单入口存在，但底层仍复用 `identity` 的管理员 session 机制

## 7. 代码边界

目录固定如下：

```text
app/admin_portal/
  routes/
  services/
templates/admin/
```

边界规则如下：

- `routes` 负责页面入口与表单提交转发
- `services` 负责调用各模块公开 service，并组装页面所需视图数据
- `templates/admin` 负责页面模板与共享布局壳
- 共享布局壳必须统一承载主题变量、通用样式和主题切换入口
- 页面模板只声明本页结构与内容区块，不重复定义整页主题级样式
- 不新增 `models` 和 `repositories`

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/admin_portal/routes/admin_login.py
app/admin_portal/routes/admin_home.py
app/admin_portal/routes/admin_identity.py
app/admin_portal/routes/admin_department.py
app/admin_portal/routes/admin_resource.py
app/admin_portal/routes/admin_system_config.py
app/admin_portal/routes/admin_reservation.py
app/admin_portal/routes/admin_checkin.py
app/admin_portal/routes/admin_statistics.py
app/admin_portal/routes/admin_violation.py
app/admin_portal/routes/admin_notification.py

app/admin_portal/routes/dependencies.py
app/admin_portal/services/menu_service.py
app/admin_portal/services/page_service.py

templates/admin/login.html
templates/admin/layout.html
templates/admin/home.html
templates/admin/user_create.html
templates/admin/departments.html
templates/admin/roles.html
templates/admin/user_roles.html
templates/admin/rooms.html
templates/admin/seats.html
templates/admin/system_configs.html
templates/admin/reservation_records.html
templates/admin/reservation_actions.html
templates/admin/checkins.html
templates/admin/statistics.html
templates/admin/violations.html
templates/admin/notifications.html
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立浏览器登录页与未登录跳转闭环
2. 建立后台基础布局与菜单渲染
3. 建立 `identity` 管理页面
4. 建立 `resource` 管理页面
5. 建立 `system_config` 管理页面
6. 建立 `reservation` 查询与代理操作页面
7. 建立 `statistics` 查询页面
8. 建立 `violation` 查询页面
9. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- `/admin/login` 页面可访问
- 未登录访问受保护管理端 HTML 页面时被重定向到登录页
- 浏览器登录成功后可进入 `/admin`
- 浏览器退出后返回登录页
- 登录管理员只能看到被授权菜单
- 无权限菜单不会展示
- 亮色/暗色主题可切换，且刷新后保持
- 关键管理端页面复用统一布局与共享控件样式
- 用户创建页面可正常访问并提交单个用户创建
- 用户创建页面选择学生账号时，可填写可选通知邮箱并保存
- 用户创建页面应清楚区分学生学号、学生通知邮箱和管理员登录标识
- 用户创建页对重复标识、无效院系和非法输入返回受控错误
- `/admin/departments` 页面可正常访问并提交院系创建、启用和停用
- 院系管理入口按 `identity.departments.write` 权限展示
- 用户创建页和自习室管理页只展示启用院系
- 自习室管理页面可正常提交创建与修改
- `/admin/rooms` 页面开放范围切换为院系专属时，当前表单所属院系下拉框可用
- 座位管理页面可正常提交创建与修改
- 系统参数页面可正常提交参数更新
- 预约记录页面可正常展示筛选结果
- 代理预约页面可正常提交代预约与代取消
- 动态签到码页面可查看指定自习室当前动态码状态、有效至时间和签到记录，且不提供生成、补签或代签到动作
- 统计页面可正常展示统计结果
- 违约记录页面无筛选时默认展示全部记录，并支持按 `user_id`、`student_no`、`room_id`、日期任意组合筛选
- 违约记录页面参数错误时返回统一 HTML 错误，不裸露 JSON
- 通知页面可展示通知日志，并可手动触发预约前提醒、未签到提醒和自动取消通知任务
- 无权限访问页面被拒绝或重定向

## 11. 完成标准

`admin_portal` 模块第一版完成时，必须满足：

- 浏览器可通过 `/admin/login` 进入登录闭环
- 未登录访问 `/admin` 等管理端 HTML 页面时会跳转到登录页
- 管理端基础布局可用
- 管理端存在统一共享布局与主题约束
- 亮色/暗色主题可切换且刷新后保持
- 菜单按权限正确渲染
- 管理端可通过独立页面创建单个学生或管理员账号
- 管理端可通过院系管理页面维护最小院系基础数据
- 院系管理菜单按 `identity.departments.write` 权限可见
- 用户创建和自习室创建的院系选项只包含启用院系
- 管理端可查询预约记录与统计结果
- 管理端可完成手动验收所需的当前动态签到码状态、签到记录、通知日志与通知任务触发核对
- 已实现业务模块具备对应后台页面
- 表单提交与服务端返回一致
- 关键管理端页面测试通过

## 12. Spec 增补（2026-04-29）

本轮补入“院系管理页面与自习室院系选择修复”能力，目标是让本地管理端完成院系基础数据闭环。

范围固定如下：

- 管理端新增 `/admin/departments` 页面。
- 页面提供最小能力：查看院系列表、新增院系、启用院系、停用院系。
- 院系页面只调用 `identity` 模块公开 `DepartmentService`，不得直接操作 repository 或 model。
- 管理端菜单和首页快捷入口加入“院系管理”，入口可见性由 `identity.departments.write` 权限控制。
- 用户创建页和自习室管理页继续只展示启用院系。
- 已停用院系不得出现在用户创建和自习室创建的院系下拉列表中。
- `/admin/rooms` 页面中“开放范围=院系专属”必须只启用当前表单内的所属院系下拉框，避免多个表单共享循环变量导致交互失效。
- 重复院系名称或编码必须展示受控 HTML 错误，不允许内部错误裸露。

不包含以下内容：

- 批量导入院系。
- 删除院系。
- 复杂组织架构或院系树。
- 新视觉体系或独立前端状态框架。
