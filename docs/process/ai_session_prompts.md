# AI Session Prompts

## 文档定位

本文档定义新对话窗口的启动方式。

本文档只负责约束 AI 如何开始工作，不负责定义项目设计本身。

项目事实来源固定为以下文档：

- `docs/tech-stack/technical_selection.md`
- `docs/architecture/project_blueprint.md`
- `docs/architecture/data_model.md`
- `docs/architecture/api_contracts.md`
- `docs/requirements/acceptance_matrix.md`
- `docs/specs/<current_module>_module_spec.md`

使用本文档时，当前模块 spec 路径不可省略。

## 使用规则

启动新窗口时，用户必须明确指定以下两项：

- 使用 `Coding Window Prompt` 或 `Review Window Prompt`
- 当前模块 spec 路径

如果当前模块 spec 路径缺失，AI 不得直接开始实现或审查。

本项目不使用单窗口角色扮演。

同一窗口不得同时充当 `coder` 和 `reviewer`。

实现与审查必须分配到两个独立窗口中完成。

## Coding Window Prompt

将下面整段复制到新的编码窗口中使用：

```text
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt，并严格按该规则工作。
当前模块 spec 路径：<SPEC_PATH>
当前任务目标：<ONE_LINE_GOAL>

你必须使用 sdd-riper-one-light 作为本轮工作方式。
先读取以下文档，读取顺序固定：
- docs/tech-stack/technical_selection.md
- docs/architecture/project_blueprint.md
- docs/architecture/data_model.md
- docs/architecture/api_contracts.md
- docs/requirements/acceptance_matrix.md
- <SPEC_PATH>

执行规则：
1. 本轮只允许处理 <SPEC_PATH> 对应模块。
2. 先做 Research 和 Plan，不要写代码。
3. 没有我发出的精确短语 `Plan Approved`，不得进入 Execute。
4. 不得修改 architecture、requirements、tech-stack 文档，除非我明确要求先改文档。
5. 所有实现必须遵守 project_blueprint 中的模块边界、依赖规则、扁平化和组合优于继承原则。
6. 查询、筛选、聚合优先在数据库层完成，不要先拉到内存中再做复杂处理。
7. 输出必须按以下顺序给出：
   - 任务理解
   - In Scope
   - Out of Scope
   - 计划修改和创建的文件路径
   - 原子化 implementation checklist
   - 测试清单
   - 风险与阻塞
8. 输出结束后停止，等待我的批准。
```

## Coding Execute Follow-up

当编码窗口完成 Plan 后，用户只发送下面这句：

```text
Plan Approved
```

收到 `Plan Approved` 后，编码窗口必须执行以下规则：

- 按已批准计划进入 Execute
- 不得私自扩大范围
- 如发现计划与现状冲突，先停止并说明冲突
- 实现结束后必须给出：
  - 实际改动文件
  - 测试执行结果
  - 与模块 spec 的一致性检查
  - 如存在偏差，明确指出偏差位置和原因
- 实现结束后，必须额外输出一个可直接转发给 `Review Window` 的标准交接块

## Review Window Prompt

将下面整段复制到新的 review 窗口中使用：

```text
请读取 docs/process/ai_session_prompts.md 中的 Review Window Prompt，并严格按该规则工作。
当前模块 spec 路径：<SPEC_PATH>
当前审查范围：<REVIEW_SCOPE>

你本轮只负责 review，不负责实现，不得直接修改代码，除非我明确要求修复。
先读取以下文档，读取顺序固定：
- docs/architecture/project_blueprint.md
- docs/architecture/data_model.md
- docs/architecture/api_contracts.md
- docs/requirements/acceptance_matrix.md
- <SPEC_PATH>

执行规则：
1. 只审查 <SPEC_PATH> 对应模块和 <REVIEW_SCOPE> 指定范围。
2. 审查重点固定为：
   - 是否越出模块边界
   - 是否违反依赖规则
   - 是否与数据模型和接口契约不一致
   - 是否缺少必要测试
   - 是否存在明显行为风险、回归风险或权限风险
3. Findings 必须按严重度排序。
4. 每条 finding 必须包含：
   - 文件路径
   - 问题描述
   - 影响
   - 修复方向
5. 如果没有发现问题，必须明确写出：
   - No findings
   - 剩余风险
   - 尚未覆盖的测试空缺
6. 不要重写需求，不要重做设计，不要给大段泛泛建议。
7. 审查结束后，必须额外输出一个可直接转发给 `Coding Window` 的标准交接块。
```

## Code To Review Handoff Format

`Coding Window` 在每次执行结束后，必须追加以下固定格式。
用户可以将这一整段直接复制到 `Review Window`。

```text
[REVIEW_HANDOFF]
SPEC_PATH: <SPEC_PATH>
REVIEW_SCOPE: <ONE_LINE_SCOPE>
CHANGED_FILES:
- <FILE_PATH_1>
- <FILE_PATH_2>
TEST_COMMANDS:
- <COMMAND_1>
- <COMMAND_2>
TEST_RESULTS:
- <RESULT_1>
- <RESULT_2>
SPEC_ALIGNMENT:
- <ALIGNMENT_POINT_1>
- <ALIGNMENT_POINT_2>
OPEN_RISKS:
- <RISK_1>
- <RISK_2>
[/REVIEW_HANDOFF]
```

约束：

- `REVIEW_SCOPE` 必须是窄范围描述，不得默认写成整个模块，除非本轮确实需要全量复审。
- `CHANGED_FILES` 必须只列本轮实际改动文件。
- `TEST_RESULTS` 必须只写本轮真实执行结果，不得写推测性结论。
- `OPEN_RISKS` 没有时写 `- None`。

## Review To Code Handoff Format

`Review Window` 在每次审查结束后，必须追加以下固定格式。
用户可以将这一整段直接复制到 `Coding Window`。

```text
[CODE_HANDOFF]
SPEC_PATH: <SPEC_PATH>
STATUS: <NO_FINDINGS|HAS_FINDINGS>
SUMMARY: <ONE_LINE_SUMMARY>
FINDINGS:
- <PRIORITY> | <FILE_PATH> | <ISSUE> | <IMPACT> | <FIX_DIRECTION>
- <PRIORITY> | <FILE_PATH> | <ISSUE> | <IMPACT> | <FIX_DIRECTION>
RESIDUAL_RISKS:
- <RISK_1>
- <RISK_2>
TEST_GAPS:
- <GAP_1>
- <GAP_2>
[/CODE_HANDOFF]
```

约束：

- `STATUS` 只能是 `NO_FINDINGS` 或 `HAS_FINDINGS`。
- 当 `STATUS=NO_FINDINGS` 时：
  - `FINDINGS` 必须只写 `- None`
- 当 `STATUS=HAS_FINDINGS` 时：
  - `FINDINGS` 必须按严重度排序
  - 每条 finding 必须可直接转成修复任务
- `RESIDUAL_RISKS` 没有时写 `- None`
- `TEST_GAPS` 没有时写 `- None`

## 最小调用方式

编码窗口最小调用句式：

```text
请读取 docs/process/ai_session_prompts.md 中的 Coding Window Prompt。
当前模块 spec 路径：docs/specs/identity_module_spec.md
当前任务目标：完成 identity 模块第一版实现。
```

Review 窗口最小调用句式：

```text
请读取 docs/process/ai_session_prompts.md 中的 Review Window Prompt。
当前模块 spec 路径：docs/specs/identity_module_spec.md
当前审查范围：identity 模块本轮全部改动文件。
```

## 双窗口循环规则

本项目使用以下固定循环：

1. `Coding Window` 先输出 Plan。
2. 用户发送 `Plan Approved` 后，`Coding Window` 执行实现与测试。
3. `Coding Window` 输出实际改动文件、测试结果、与 spec 的一致性说明，并追加 `REVIEW_HANDOFF`。
4. 用户将 `REVIEW_HANDOFF` 整段复制到 `Review Window`。
5. `Review Window` 只基于真实文件和指定范围做审查，并追加 `CODE_HANDOFF`。
6. 用户将 `CODE_HANDOFF` 整段复制到 `Coding Window`。
7. 如 `CODE_HANDOFF` 中存在 findings，`Coding Window` 只修复其中问题。
8. 如 `Review Window` 输出 `No findings`，当前模块本轮收口。

用户可以自行控制循环次数。

如同一 finding 连续多轮未收敛，应暂停实现并回到 spec 检查边界或规则是否缺失。
