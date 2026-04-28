# Assistant Module Spec

## 1. 任务定位

本文件定义 `assistant` 模块第一版实现的边界。

本模块在当前阶段负责提供以下能力：

- 自然语言查询入口
- 基于规则和关键词的意图识别
- 查询请求到内部业务 service 的转发
- 查询结果的统一返回

## 2. 实现范围

本次实现只包含以下内容：

- 学生端自然语言查询接口
- 基于关键词和规则的意图识别
- 空座查询意图处理
- 座位属性查询意图处理
- 本人今日预约查询意图处理

本次实现不包含以下内容：

- 大语言模型接入
- 多轮对话记忆
- 复杂对话管理
- 管理端助手页面
- 通用问答能力
- 非查询类操作执行

### 2.1 首版意图范围

第一版固定只支持以下意图：

- `QUERY_AVAILABLE_SEATS`
- `QUERY_WINDOW_SEATS`
- `QUERY_TODAY_MY_RESERVATION`

对应目标如下：

- 查询今晚可用座位
- 查询靠窗座位
- 查询本人今日预约

### 2.2 实现方式约束

- 第一版只允许使用关键词匹配、规则判断和参数抽取
- 不要求接入大模型
- 若后续接入大模型，必须保持现有接口与返回结构稳定

## 3. 查询规则

查询规则固定如下：

### 3.1 空座查询

- “今天晚上还有空座吗”类输入必须路由到空座查询意图
- 查询必须通过 `resource` 和 `reservation` 的公开 service 组合完成
- 返回结果至少包含：
  - 座位编号
  - 自习室
  - 可用时间段

### 3.2 属性查询

- “帮我找靠窗的座位”类输入必须路由到属性查询意图
- 属性筛选通过 `resource` 公开 service 完成
- 第一版至少支持：
  - 靠窗
  - 固定插座
  - 移动导轨插座

### 3.3 本人预约查询

- “我今天定了哪里的座位”类输入必须路由到本人今日预约查询意图
- 查询必须只返回当前登录学生自己的数据
- 查询通过 `reservation` 公开 service 完成

### 3.4 失败回退规则

- 无法识别的输入必须返回受控失败结果
- 不得编造查询结果
- 不得越权查询其他用户数据

## 4. 模块边界

- `assistant` 可以依赖 `resource`
- `assistant` 可以依赖 `reservation`
- `assistant` 不依赖 `identity`
- `assistant` 不依赖 `system_config`
- `assistant` 不依赖 `checkin`
- `assistant` 不依赖 `violation`
- `assistant` 不依赖 `notification`

跨模块协作规则固定如下：

- 当前登录学生身份通过学生端认证上下文提供，不由 `assistant` 重复实现认证逻辑
- `assistant` 只调用其他模块公开 service
- `assistant` 不直接调用任何模块的 repository
- `assistant` 不直接修改任何业务 model 状态

## 5. 数据模型范围

本模块第一版不新增业务数据模型。

本模块只消费其他业务模块公开的数据结构，并在本模块内定义请求/响应 schema。

## 6. 对外接口

本模块第一版实现以下接口：

### 学生端

- `POST /student/assistant/query`

输入核心字段：

- `message`

返回核心字段：

- `intent`
- `result_type`
- `result`

说明：

- 第一版只做同步查询请求
- 第一版不支持多轮会话 id

## 7. 代码边界

目录固定如下：

```text
app/modules/assistant/
  api/
  schemas/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责意图识别、参数抽取、查询转发和结果组装
- `schemas` 负责定义请求与响应结构
- 第一版不新增 `models` 和 `repositories`

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/assistant/schemas/query.py

app/modules/assistant/services/intent_service.py
app/modules/assistant/services/query_service.py

app/modules/assistant/api/student_assistant.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 assistant 请求/响应 schema
2. 建立意图识别与参数抽取 service
3. 建立查询转发与结果组装 service
4. 建立学生端查询接口
5. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 输入“今天晚上还有空座吗”可识别为空座查询意图
- 输入“帮我找靠窗的座位”可识别为属性查询意图
- 输入“我今天定了哪里的座位”可识别为本人预约查询意图
- 空座查询返回可用座位结果
- 属性查询返回符合条件座位结果
- 本人预约查询只返回当前用户数据
- 无法识别输入返回受控失败结果
- 不得返回编造结果

## 11. 完成标准

`assistant` 模块第一版完成时，必须满足：

- 学生可以通过自然语言触发三类查询
- 意图识别可用
- 查询转发可用
- 返回结构稳定
- 关键助手测试通过
