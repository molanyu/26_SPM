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
| US-02 | G2 | `resource` | `GET /student/rooms/{room_id}/seats` | 返回指定自习室座位及状态，支持指定时段查询 | 座位状态查询测试 |
| US-03 | G4 | `reservation` | `POST /student/reservations` | 学生可以在规则允许范围内创建预约 | 创建预约测试、冲突测试 |
| US-04 | G5 | `checkin` | `POST /student/checkins/code` `POST /student/checkins/qrcode` | 已预约用户可在有效时段内签到 | 动态码签到测试、二维码签到测试 |
| US-05 | G6 | `notification` | 内部任务 | 预约开始前 15 分钟触发提醒；启用 `smtp_email` 通道时可真实发送邮件提醒，邮件主题和正文应为面向用户的中文内容 | 提醒任务测试、SMTP 通道测试、邮件内容格式测试 |
| US-06 | G5 | `checkin` `violation` `notification` | 内部任务 | 开始后 10 分钟提醒，15 分钟未签到自动取消并生成违约；启用 `smtp_email` 通道时可真实发送提醒/通知，邮件主题和正文应清楚说明事件含义 | 超时释放测试、违约生成测试、SMTP 通道测试、邮件内容格式测试 |
| US-07 | G2 | `resource` | `GET /student/rooms/{room_id}/seats` | 支持按靠窗和插座筛选座位 | 属性筛选测试 |
| US-08 | G4 | `reservation` `student_miniprogram` | `GET /student/reservations/current` `GET /student/reservations/history` `POST /student/reservations` | 学生可查看当前有效预约、历史预约并再次预约 | 当前预约查询测试、历史查询测试、再次预约测试 |
| US-09 | G1 | `identity` | `GET /student/me` `GET /student/rooms` | 院系用户只能访问对应院系自习室 | 院系权限测试 |
| US-10 | G4 | `reservation` | `POST /student/reservations/{reservation_id}/cancel` | 学生可在预约开始前主动取消预约 | 主动取消测试 |
| US-11 | G2 | `resource` | `POST /admin/rooms` `PUT /admin/rooms/{room_id}` `POST /admin/rooms/{room_id}/deactivate` | 管理员可创建、修改、注销自习室 | 自习室 CRUD 测试 |
| US-12 | G2 | `resource` | `POST /admin/seats` `PUT /admin/seats/{seat_id}` `POST /admin/seats/{seat_id}/deactivate` | 管理员可创建、修改、注销座位并维护属性 | 座位 CRUD 测试 |
| US-13 | G3 | `system_config` | `GET /admin/system-configs` `PUT /admin/system-configs/{config_key}` | 管理员可查询并修改系统参数 | 参数更新测试 |
| US-14 | G6 | `violation` `reservation` `admin_portal` | `GET /admin/reservations` `GET /admin/reservations/records` `GET /admin/violations` | 管理员可按条件查询预约记录和违约记录 | 预约记录筛选测试、违约记录筛选测试 |
| US-15 | G4 | `reservation` | `POST /admin/reservations` `POST /admin/reservations/{reservation_id}/cancel` | 管理员可代预约和代取消 | 代理操作测试 |
| US-16 | G7 | `violation` `resource` `admin_portal` | `GET /admin/statistics/usage` `GET /admin/statistics` | 管理员可查看使用率和违约率统计 | 统计查询测试、管理端统计页测试 |
| US-17 | G1 | `identity` | `GET /admin/roles` `POST /admin/roles` `PUT /admin/roles/{role_id}` `POST /admin/roles/{role_id}/deactivate` | 系统管理员可创建、修改并停用角色 | 角色管理测试 |
| US-18 | G1 | `identity` | `POST /admin/users/{user_id}/roles` | 系统管理员可给用户分配角色 | 用户角色分配测试 |
| US-19 | G1 | `identity` `admin_portal` | `GET /admin/me` | 管理员仅看到被授权菜单且写操作受服务端权限保护 | 菜单权限测试、接口权限测试 |
| US-25 | G1 | `identity` `admin_portal` | `GET /admin/users/new` `POST /admin/users` | 系统管理员可通过管理端创建单个学生或管理员账号；学生账号可选填写通知邮箱但仍使用学号登录；重复登录标识、重复通知邮箱、无效院系和非法输入需受控失败，且响应不返回原始密码 | 用户创建接口测试、管理端用户创建页面测试、通知邮箱字段测试 |
| US-20 | G8 | `assistant` | `POST /student/assistant/query` | 输入“今天晚上还有空座吗”能返回空座结果 | 意图识别测试、空座查询测试 |
| US-21 | G8 | `assistant` | `POST /student/assistant/query` | 输入“帮我找靠窗的座位”能返回符合条件座位 | 意图识别测试、属性查询测试 |
| US-22 | G8 | `assistant` | `POST /student/assistant/query` | 输入“我今天定了哪里的座位”能返回本人今日预约 | 意图识别测试、个人预约查询测试 |
| US-23 | G5 | `checkin` | 内部任务 `POST /student/checkins/code` | 系统能生成每日动态码并完成校验 | 动态码生成测试、校验测试 |
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
