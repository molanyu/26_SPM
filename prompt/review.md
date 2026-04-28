# Identity

# Resource
请读取 docs/process/ai_session_prompts.md 中的 Review Window Prompt，并严格按该规则工作。

当前模块 spec 路径：docs/specs/resource_module_spec.md
当前审查范围：resource 模块本轮全部改动文件。

补充约束：
- 重点检查 resource 是否越界依赖 reservation。
- 重点检查可见性规则是否正确依赖 identity，而不是把权限逻辑写散。
- 重点检查自习室/座位 CRUD、可见性过滤、属性筛选、seat_code 唯一性是否符合 spec。
- 重点检查 student seat status 是否被错误实现为预约状态。
- 审查结束后必须追加标准 CODE_HANDOFF 块。


# Checkin(由CODE窗口给出)
[REVIEW_HANDOFF]
SPEC_PATH: docs/specs/checkin_module_spec.md
REVIEW_SCOPE: checkin G5 第一版实现及为满足公共协作边界新增的 reservation/resource/violation public service
CHANGED_FILES:

app/main.py
app/modules/reservation/schemas/reservation.py
app/modules/reservation/repositories/reservation_repository.py
app/modules/reservation/services/init.py
app/modules/reservation/services/checkin_access_service.py
app/modules/resource/repositories/room_repository.py
app/modules/resource/services/init.py
app/modules/resource/services/checkin_room_service.py
app/modules/violation/init.py
app/modules/violation/services/init.py
app/modules/violation/services/checkin_violation_service.py
app/modules/checkin/init.py
app/modules/checkin/api/init.py
app/modules/checkin/api/router.py
app/modules/checkin/api/student_checkin.py
app/modules/checkin/models/init.py
app/modules/checkin/models/checkin_code.py
app/modules/checkin/models/checkin_record.py
app/modules/checkin/schemas/init.py
app/modules/checkin/schemas/checkin.py
app/modules/checkin/repositories/init.py
app/modules/checkin/repositories/checkin_code_repository.py
app/modules/checkin/repositories/checkin_record_repository.py
app/modules/checkin/services/init.py
app/modules/checkin/services/code_service.py
app/modules/checkin/services/checkin_service.py
app/modules/checkin/services/timeout_service.py
app/modules/checkin/tasks/init.py
app/modules/checkin/tasks/daily_code_task.py
app/modules/checkin/tasks/timeout_release_task.py
tests/checkin/test_student_checkin.py
tests/checkin/test_code_task.py
tests/checkin/test_timeout_service.py
TEST_COMMANDS:
pytest -q tests/checkin -p no:cacheprovider
pytest -q -p no:cacheprovider
TEST_RESULTS:
9 passed in 6.15s
62 passed in 49.43s
SPEC_ALIGNMENT:
已实现每日动态签到码生成、动态码签到、二维码签到、签到校验、签到成功后预约状态更新、超时未签到预约释放
checkin 通过 reservation/resource/violation 的公开 service 协作，未直接跨模块调用 repository
checkin_grace_minutes 和 violation_threshold_minutes 均通过 system_config 的公开 service 获取
超时释放只把预约状态更新为 EXPIRED，并通过 violation 公开 service 触发协作，没有写入 notification 逻辑
OPEN_RISKS:
violation public service 当前仅提供协作 hook，真实违约落账持久化将在 violation 模块实现时补齐
[/REVIEW_HANDOFF]