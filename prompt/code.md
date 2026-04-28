# Identity


# Resource
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/resource_module_spec.md
当前任务目标：完成 resource 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity 模块已有通过内容。
- 严格按 docs/specs/resource_module_spec.md 实现。
- resource 只负责资源模型、可见性、开放时间、座位属性筛选和管理端资源维护。
- resource 不得依赖 reservation。
- GET /student/rooms/{room_id}/seats 中的 status 在 G2 阶段只允许表达资源侧状态，不允许引入预约占用计算。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# System
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/system_config_module_spec.md
当前任务目标：完成 system_config 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity 和 resource 模块已有通过内容。
- 严格按 docs/specs/system_config_module_spec.md 实现。
- system_config 只负责配置值的存储、读取、更新和校验，不负责预约、签到、违约、提醒的业务规则判定。
- 其他模块读取配置时只能通过 system_config 的公开 service，不允许跨模块直接访问 repository。
- 首版只实现以下配置项：
  - max_reservation_hours
  - checkin_grace_minutes
  - violation_threshold_minutes
- 更新时必须校验 value_type 和参数范围。
- violation_threshold_minutes 不得小于 checkin_grace_minutes。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# Reservation
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/reservation_module_spec.md
当前任务目标：完成 reservation 模块在 G4 阶段的第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config 模块已有通过内容。
- 严格按 docs/specs/reservation_module_spec.md 实现。
- reservation 只负责：
  - 学生创建预约
  - 学生主动取消预约
  - 管理员代预约
  - 管理员代取消预约
  - 历史预约查询
  - 冲突校验
  - 预约规则校验
- reservation 不负责：
  - 当前有效预约查询
  - 管理员预约记录筛选查询
  - 签到
  - 超时释放
  - 违约记录
  - 提醒通知
- 预约时间必须按整点小时提交。
- 单次预约时长不得超过 system_config.max_reservation_hours。
- 预约时间必须落在自习室开放时间范围内。
- 学生只能预约自己可见范围内的自习室和座位。
- 冲突校验必须在数据库查询层完成，不允许把大量记录拉到内存后再判断。
- 状态边界必须固定：
  - G4 只负责 BOOKED 和 CANCELLED
  - CHECKED_IN 不属于本轮
  - EXPIRED 不属于本轮
- “再次预约”不新增独立接口，历史复用通过已有创建预约接口完成。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。


# Chekin
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/checkin_module_spec.md
当前任务目标：完成 checkin 模块在 G5 阶段的第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config、reservation 模块已有通过内容。
- 严格按 docs/specs/checkin_module_spec.md 实现。
- checkin 只负责：
  - 每日动态签到码生成
  - 动态码签到
  - 二维码签到
  - 签到校验
  - 签到成功后预约状态更新
  - 超时未签到预约释放
- checkin 不负责：
  - 预约创建与取消
  - 预约历史查询
  - 提醒发送
  - 违约记录查询与统计
  - 管理端签到记录页面
- 学生只能对自己的 BOOKED 预约执行签到。
- 已取消、已签到、已过期预约不得签到。
- checkin_grace_minutes 必须通过 system_config 的公开 service 获取。
- 动态码或二维码都必须与预约所属自习室匹配。
- 同一自习室同一天只允许一个有效动态码。
- 同一预约成功签到后不得再次生成第二条有效签到记录。
- 超时释放只负责把预约状态更新为 EXPIRED。
- 违约落账不由 checkin 直接写表，必须通过 violation 的公开 service 触发协作。
- 提醒不属于 checkin 职责，不要把 notification 逻辑写进来。
- 不允许跨模块直接调用 repository。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# Violation
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/violation_module_spec.md
当前任务目标：完成 violation 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config、reservation、checkin 模块已有通过内容。
- 严格按 docs/specs/violation_module_spec.md 实现。
- violation 第一版只负责：
  - 超时未签到违约记录落账
  - 管理端违约记录查询
  - 对 checkin 暴露公开违约落账 service
- violation 第一版不负责：
  - 违约率统计
  - 使用率统计
  - 提醒通知
  - 管理端统计大盘
  - 复杂违约类型体系
- 当前只支持一种违约类型：NO_SHOW_TIMEOUT。
- 同一预约最多只能生成一条同类型违约记录。
- 学生主动取消预约不得生成违约记录。
- 已签到预约不得生成违约记录。
- 管理端查询至少支持：
  - user_id
  - room_id
  - date_from
  - date_to
- violation 不直接写 reservation 状态。
- checkin 只能通过 violation 的公开 service 触发违约落账。
- 不允许跨模块直接调用 repository。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# Notification
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/notification_module_spec.md
当前任务目标：完成 notification 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config、reservation、checkin、violation 模块已有通过内容。
- 严格按 docs/specs/notification_module_spec.md 实现。
- notification 第一版只负责：
  - 预约前提醒
  - 未签到提醒
  - 自动取消后的通知
  - NotificationLog 落账
- notification 第一版不负责：
  - 真实邮件服务接入
  - 真实微信订阅消息接入
  - 用户通知偏好设置
  - 管理端通知运营页面
  - 通知模板管理后台
- 第一版固定通知类型：
  - RESERVATION_REMINDER
  - NO_SHOW_REMINDER
  - AUTO_CANCEL_NOTICE
- 第一版实际发送通道采用受控 mock/log 方式，但必须落 NotificationLog。
- 同一预约同一通知类型只允许生成一次成功通知记录。
- 预约前提醒只在开始前 15 分钟窗口触发。
- 未签到提醒只在开始后 10 分钟且仍未签到时触发。
- 自动取消通知只在预约状态已完成更新后触发。
- notification 不直接调用其他模块 repository，不直接修改其他模块 model 状态。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# AdminPortal
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/admin_portal_module_spec.md
当前任务目标：完成 admin_portal 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config、reservation、checkin、violation、notification 模块已有通过内容。
- 严格按 docs/specs/admin_portal_module_spec.md 实现。
- admin_portal 第一版只负责：
  - 管理端基础布局
  - 菜单按权限渲染
  - 已实现业务模块的后台页面与表单适配
- admin_portal 第一版不负责：
  - 核心业务规则判定
  - 直接数据库读写
  - 统计大盘页面
  - 通知运营页面
  - 助手管理页面
  - 复杂前端状态管理框架
- admin_portal 只能调用各模块公开 service：
  - identity
  - resource
  - system_config
  - reservation
  - violation
- 不允许直接调用任何模块 repository。
- 不允许直接修改任何业务 model 状态。
- 页面只负责展示、收集表单输入和调用公开 service，不复制核心业务规则。
- 菜单必须基于 identity 返回的菜单权限渲染。
- 即使菜单隐藏，服务端权限校验仍必须保留。
- 本轮只交付以下页面：
  - /admin
  - /admin/roles
  - /admin/users/{user_id}/roles
  - /admin/rooms
  - /admin/seats
  - /admin/system-configs
  - /admin/reservations/actions
  - /admin/violations
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。



# Assistant
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/assistant_module_spec.md
当前任务目标：完成 assistant 模块第一版实现。

补充约束：
- 本轮是新模块实现，不要改动 identity、resource、system_config、reservation、checkin、violation、notification、admin_portal 模块已有通过内容。
- 严格按 docs/specs/assistant_module_spec.md 实现。
- assistant 第一版只负责：
  - 学生端自然语言查询接口
  - 基于关键词和规则的意图识别
  - 空座查询意图处理
  - 座位属性查询意图处理
  - 本人今日预约查询意图处理
- assistant 第一版不负责：
  - 大语言模型接入
  - 多轮对话记忆
  - 复杂对话管理
  - 管理端助手页面
  - 通用问答能力
  - 非查询类操作执行
- 第一版固定只支持以下意图：
  - QUERY_AVAILABLE_SEATS
  - QUERY_WINDOW_SEATS
  - QUERY_TODAY_MY_RESERVATION
- 第一版只允许使用关键词匹配、规则判断和参数抽取。
- assistant 只能依赖 resource 和 reservation 的公开 service。
- assistant 不允许直接调用任何模块 repository。
- assistant 不允许直接修改任何业务 model 状态。
- 查询失败时必须返回受控失败结果，不得编造结果。
- Plan 批准后再进入实现。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# Tests
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/tests_devops_module_spec.md
当前任务目标：完成 tests/devops 阶段的第一版实现。

补充约束：
- 本轮是收口阶段，不要修改各业务模块已经通过 review 的业务语义。
- 严格按 docs/specs/tests_devops_module_spec.md 实现。
- tests/devops 第一版只负责：
  - 统一 pytest 测试入口
  - 关键模块自动化测试收口
  - 最小 CI 工作流
  - 测试与流水线说明文档
- tests/devops 第一版不负责：
  - 自动部署到云端
  - 蓝绿发布
  - 性能压测流水线
  - 安全扫描平台接入
  - 多环境发布审批流
- 关键模块至少包括：
  - identity
  - resource
  - system_config
  - reservation
  - checkin
  - violation
  - notification
  - assistant
- admin_portal 只要求基础页面与权限测试，不要求完整端到端 UI 自动化。
- 必须存在统一测试命令，并且本地和 CI 使用同一套命令。
- 测试失败时，CI 必须失败。
- 不允许通过跳过核心测试来伪造绿色流水线。
- 如需补测试，优先补到对应模块 tests/<module>/ 下；不要为了收口去改业务规则。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

# Statistics
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/statistics_module_spec.md
当前任务目标：完成 G7 统计分析第一版实现。

补充约束：
- 本轮是在既有模块基础上补统计能力，不要修改已经通过 review 的业务语义。
- 严格按 docs/specs/statistics_module_spec.md 实现。
- G7 第一版只负责：
  - 管理端 `GET /admin/statistics/usage` 统计查询入口
  - 自习室使用率统计
  - 座位使用率统计
  - 违约率统计
  - 对应的统计 schema、聚合查询、service 编排与基础测试
- G7 第一版不负责：
  - 管理端图表大盘页面
  - 导出 Excel 或报表下载
  - 实时占用看板
  - 趋势预测与同比环比分析
  - 资源开放时间与启停历史版本回放
  - 多租户、多校区、多层级组织统计
- 本轮不新增新的一级业务模块。
- `violation` 负责管理端统计接口与统计编排。
- `resource` 只负责提供统计所需的资源维度只读查询能力。
- 不允许直接跨模块调用对方 repository。
- 不允许新增跨模块写操作。
- admin_portal 如未被当前 spec 明确要求，不要扩展管理端页面实现。
- 聚合、筛选、比率计算优先在数据库层完成，不要把大量数据拉到内存中再统计。
- 统计查询只允许管理员访问；学生端不暴露统计接口。
- 取消预约不计入使用率分子；违约率只统计 `NO_SHOW_TIMEOUT`。
- 如需补测试，优先补到对应模块 tests/ 下；不要为了让测试通过去改业务规则。
- 如果发现必须修改 architecture、requirements、tech-stack 文档，先停止并说明原因。
- 如果发现现有 `project_blueprint.md` 或 `api_contracts.md` 与 G7 所需的只读协作边界或统计参数定义冲突，先停止并说明冲突，不要绕过文档直接实现。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。


# Debug
## Admin login 4/20
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/admin_portal_module_spec.md
当前任务目标：补齐管理端浏览器登录闭环，并先修正相关 spec/document 缺口。

补充约束：
- 本轮不要处理 statistics_module_spec.md，也不要扩展统计功能。
- 当前问题是：
  1. /admin 已存在，但未登录时直接返回 unauthenticated JSON
  2. 当前没有明确的管理端浏览器登录页闭环
  3. 当前运行库中也没有现成管理员账号可直接进入后台
- 本轮必须先检查并补齐以下文档，再进入代码实现：
  - docs/specs/admin_portal_module_spec.md
  - docs/specs/identity_module_spec.md
  - docs/architecture/api_contracts.md
  - docs/delivery/delivery_guide.md
- 需要在 spec 中明确：
  - 是否提供 GET /admin/login
  - 管理端浏览器登录路径
  - 未登录访问 /admin 时的行为
  - 登录成功/退出后的跳转行为
  - 管理员初始化与演示账号使用方式
- 代码实现只做最小闭环，不扩展完整用户管理系统。
- 保持现有 admin session 机制，不改成新的认证体系。
- 管理端应支持浏览器正常登录进入后台。
- 对 HTML 页面请求，未登录访问 /admin 时应跳转到登录页，而不是直接返回裸 JSON 错误。
- 对纯接口请求，保持受控错误响应，不要破坏现有 API 边界。
- 如当前运行库中没有管理员账号，需要补一个受控初始化方案或明确现有 bootstrap 的使用路径。
- 不新增新的一级业务模块。
- 如果发现必须修改 architecture、requirements、tech-stack 文档以外的顶层边界，先停止并说明原因。
- Plan 批准后再进入实现。
- 实现完成后必须追加标准 REVIEW_HANDOFF 块。

本轮完成标准：
- spec/document 已补齐
- 浏览器可访问 /admin/login
- 管理员可登录并进入 /admin
- 未登录访问 /admin 时会跳转
- 交付文档写明管理员初始化和登录路径


## UI 4/21
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。
当前模块 spec 路径：docs/specs/admin_portal_module_spec.md

当前任务目标：
继续增量修复 admin_portal 的整体布局与视觉一致性问题。当前角色管理已有改善，但“创建后立即启用”控件仍然难看，座位管理等其他页面也没有统一到同一套设计语言。请建立共享的后台主题/布局约束，并加入亮色/暗色主题切换。

补充约束：
- 同时遵守 docs/specs/resource_module_spec.md、docs/specs/identity_module_spec.md、docs/architecture/api_contracts.md
- 这是已有模块的增量 UI 重构，不要改成 SPA，不要引入前端框架
- 需要建立一个共享的后台设计源文件（可为共享样式文件，或从 layout.html 中抽离），用于统一：
  - 颜色 token
  - 字体层级
  - 间距体系
  - 卡片/表单/按钮/开关/筛选条/状态标签
- 加入主题切换：
  - light：浅色莫兰迪色系，清爽、美观、柔和
  - dark：沿用当前深色方向，但提高层级、对比和精致度
- 主题切换需要持久化，刷新后保持
- 优先重做这些高频丑控件：
  - “创建后立即启用”改成更紧凑、美观的开关样式
  - 座位管理中的属性选项改成规整统一的 toggle 组件，不要再出现笨重的大圆块
  - 角色管理、房间管理、座位管理共用同一套表单与筛选布局
- 保持现有权限、会话、路由和服务端渲染结构不变
- 不要顺手扩展无关业务功能

本轮完成标准：
- 后台存在统一的共享主题/布局约束源，而不是每页各写各的
- 亮色/暗色主题都可用，且亮色为浅色莫兰迪风格
- “创建后立即启用”控件明显比现在更精致、更轻、更符合后台表单语义
- 角色管理、房间管理、座位管理三页的视觉语言统一
- 座位管理页面不再出现当前这种笨重、低级感强的属性按钮组
- 输出改动文件、测试结果、与 spec 一致性说明，并追加 REVIEW_HANDOFF