# 验收矩阵

## 1. 文档定位

本文件用于建立用户故事、交付单元、接口和测试之间的映射关系。

本文件用于回答以下问题：

- 每个用户故事由哪个交付单元负责
- 每个用户故事由哪些模块实现
- 每个用户故事对应哪些接口
- 每个用户故事如何验收
- 每个用户故事至少需要哪些测试

## 2. 验收规则

- 每个用户故事至少对应一条明确验收标准
- 每个用户故事至少对应一组可执行测试
- 每个交付单元未完成全部对应故事的验收，不进入下一个交付单元
- 验收优先按用户故事进行，不按页面完成度进行

## 3. 验收矩阵

| Story | Group | Module | 主要接口 | 验收标准 | 最少测试 |
| --- | --- | --- | --- | --- | --- |
| US-01 | G2 | `resource` | `GET /student/rooms` | 学生只能看到自己有权限访问的自习室列表 | 可见性查询测试 |
| US-02 | G2/G4 | `resource` `reservation` | `GET /student/rooms/{room_id}/seats` `GET /student/rooms/{room_id}/seat-availability` | `resource` 返回指定自习室座位及资源侧状态；`reservation` 组合资源基础信息与预约占用，返回指定时段最终可用状态 | 资源侧座位状态查询测试、指定时段可用状态查询测试 |
| US-03 | G4 | `reservation` | `POST /student/reservations` `POST /admin/reservations` | 学生和管理员可以在规则允许范围内创建预约；预约时间支持 30 分钟粒度；过去或已开始时间段必须被拒绝 | 创建预约测试、30 分钟粒度测试、过去时间拒绝测试、冲突测试 |
| US-04 | G5 | `checkin` `admin_portal` | `POST /student/checkins/code` `POST /student/checkins/qrcode` `GET /admin/checkins` | 已预约用户可在有效时段内使用当前 5 分钟动态码签到；管理端可查看指定自习室当前动态码状态、有效至时间和签到记录，不提供生成签到码动作 | 动态码窗口稳定/轮换测试、动态码签到测试、二维码签到测试、管理端动态码状态页测试 |
| US-05 | G6 | `notification` `admin_portal` | 后台调度任务 `GET /admin/notifications` | 预约开始前 15 分钟由后台调度器自动触发提醒；启用 `smtp_email` 通道时可真实发送邮件提醒；管理端只查看通知日志，不提供手动触发任务 | 调度器 tick 测试、提醒任务测试、SMTP 通道测试、邮件内容格式测试、通知日志页面测试 |
| US-06 | G5 | `checkin` `violation` `notification` `admin_portal` | 后台调度任务 `GET /admin/violations` `GET /admin/notifications` | 开始后 10 分钟由后台调度器自动提醒，15 分钟未签到后系统自动将预约置为过期并释放座位，同时生成违约；违约页默认显示全部并支持学生学号/自习室/日期组合筛选；通知日志可解释未收到邮件原因 | 超时释放调度测试、违约生成测试、违约筛选 UX 测试、SMTP 通道测试、通知日志测试 |
| US-07 | G2 | `resource` | `GET /student/rooms/{room_id}/seats` | 支持按靠窗和插座筛选座位 | 属性筛选测试 |
| US-08 | G4 | `reservation` `student_miniprogram` | `GET /student/reservations/current` `GET /student/reservations/history` `POST /student/reservations` | 学生可查看当前有效预约、历史预约并再次预约 | 当前预约查询测试、历史查询测试、再次预约测试 |
| US-09 | G1 | `identity` `admin_portal` `resource` | `GET /student/me` `GET /student/rooms` `GET /admin/departments` `POST /admin/departments` `POST /admin/departments/{department_id}/activate` `POST /admin/departments/{department_id}/deactivate` | 系统管理员可维护最小院系基础数据；院系用户只能访问对应院系自习室；停用院系不进入用户创建和自习室创建可选列表 | 院系权限测试、院系管理测试、停用院系不可选测试 |
| US-10 | G4 | `reservation` | `POST /student/reservations/{reservation_id}/cancel` | 学生可在预约开始前主动取消预约 | 主动取消测试 |
| US-11 | G2 | `resource` | `POST /admin/rooms` `PUT /admin/rooms/{room_id}` `POST /admin/rooms/{room_id}/deactivate` | 管理员可创建、修改、注销自习室；院系专属自习室只能选择启用院系；管理端 rooms 表单切换为院系专属后当前表单院系下拉可用 | 自习室 CRUD 测试、停用院系拒绝测试、rooms 院系联动测试 |
| US-12 | G2 | `resource` | `POST /admin/seats` `PUT /admin/seats/{seat_id}` `POST /admin/seats/{seat_id}/deactivate` | 管理员可创建、修改、注销座位并维护属性 | 座位 CRUD 测试 |
| US-13 | G3 | `system_config` | `GET /admin/system-configs` `PUT /admin/system-configs/{config_key}` | 管理员可查询并修改系统参数 | 参数更新测试 |
| US-14 | G6 | `violation` `reservation` `admin_portal` | `GET /admin/reservations` `GET /admin/reservations/records` `GET /admin/violations` | 管理员可按条件查询预约记录和违约记录；违约记录无筛选时显示全部且 HTML 错误不返回裸 JSON | 预约记录筛选测试、违约记录筛选测试、违约页 HTML 错误测试 |
| US-15 | G4 | `reservation` | `POST /admin/reservations` `POST /admin/reservations/{reservation_id}/cancel` | 管理员可代预约和代取消 | 代理操作测试 |
| US-16 | G7 | `violation` `resource` `admin_portal` | `GET /admin/statistics/usage` `GET /admin/statistics` | 管理员可查看使用率和违约率统计 | 统计查询测试、管理端统计页测试 |
| US-17 | G1 | `identity` | `GET /admin/roles` `POST /admin/roles` `PUT /admin/roles/{role_id}` `POST /admin/roles/{role_id}/deactivate` | 系统管理员可创建、修改并停用角色 | 角色管理测试 |
| US-18 | G1 | `identity` | `POST /admin/users/{user_id}/roles` | 系统管理员可给用户分配角色 | 用户角色分配测试 |
| US-19 | G1 | `identity` `admin_portal` | `GET /admin/me` `GET /admin/departments` | 管理员仅看到被授权菜单且写操作受服务端权限保护；院系管理入口由 `identity.departments.write` 控制 | 菜单权限测试、接口权限测试、院系菜单权限测试 |
| US-25 | G1 | `identity` `admin_portal` | `GET /admin/users/new` `POST /admin/users` | 系统管理员可通过管理端创建单个学生或管理员账号；学生账号可选填写通知邮箱但仍使用学号登录；重复登录标识、重复通知邮箱、无效院系和非法输入需受控失败，且响应不返回原始密码；用户创建页只展示启用院系 | 用户创建接口测试、管理端用户创建页面测试、通知邮箱字段测试、启用院系选项测试 |
| US-20 | G8 | `assistant` `student_miniprogram` | `POST /student/assistant/query` | 输入“今天晚上还有空座吗”能返回空座结果，小程序以用户卡片/列表展示而非 raw JSON | 意图识别测试、空座查询测试、助手 UI 渲染测试 |
| US-21 | G8 | `assistant` `student_miniprogram` | `POST /student/assistant/query` | 输入“帮我找靠窗的座位”能返回符合条件座位，小程序以用户卡片/列表展示而非 raw JSON | 意图识别测试、属性查询测试、助手 UI 渲染测试 |
| US-22 | G8 | `assistant` `student_miniprogram` | `POST /student/assistant/query` | 输入“我今天定了哪里的座位”能返回本人今日预约，小程序以用户卡片/列表/空状态展示 | 意图识别测试、个人预约查询测试、助手 UI 渲染测试 |
| US-23 | G5 | `checkin` | `POST /student/checkins/code` | 系统能按自习室和 5 分钟时间片派生动态码并完成校验；同一时间片稳定，跨时间片变化，不同自习室不同 | 动态码时间片派生测试、校验测试、过期时间片拒绝测试 |
| US-24 | G9 | `tests` `devops` | 测试命令与流水线 | 项目关键模块具备自动化测试并进入流水线 | 单元测试执行、流水线执行测试 |

## 4. 交付门槛

每个交付单元进入完成状态前，必须满足：

- 组内全部用户故事均可映射到接口或任务入口
- 组内全部用户故事均有明确验收标准
- 组内全部用户故事均有对应测试
- 至少完成一轮人工验收和一轮自动化测试

## 5. 变更规则

用户故事变更时，必须同步更新本文件中的：

- 分组映射
- 接口映射
- 验收标准
- 测试映射

更新完成后再修改代码和测试。
