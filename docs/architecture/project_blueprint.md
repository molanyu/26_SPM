# 项目蓝图

## 1. 文档定位

本文件是项目的架构主规格。

作用只有三个：

- 定义系统边界
- 定义模块边界
- 定义代码组织和变更规则

后续开发统一遵循以下顺序：

1. 先更新用户故事
2. 再更新本文件
3. 再修改代码和测试

## 2. 架构原则

本项目采用以下固定原则：

- 模块化单体
- 扁平化设计
- 高内聚、低耦合
- 组合优于继承
- 显式边界、显式依赖、显式查询

具体约束如下：

- 不采用微服务
- 不采用深层继承结构
- 不通过隐式机制传递核心业务规则
- 不把多个模块的逻辑堆到同一个大文件中
- 不允许模块跨边界直接修改其他模块内部实现

## 3. 系统边界

系统由一个后端服务、一个数据库和两个前端入口组成：

- 学生端：微信小程序
- 管理端：服务端渲染页面
- 后端：统一业务服务
- 数据库：PostgreSQL

系统中的核心能力包括：

- 用户认证与权限控制
- 自习室与座位管理
- 预约与取消预约
- 动态码签到
- 超时释放与违约记录
- 提醒通知
- 自然语言查询

## 4. 代码组织规则

后端统一按模块组织，每个模块内部按职责分层：

- `api`：接口层
- `schemas`：输入输出模型
- `services`：业务规则
- `repositories`：数据库读写与查询
- `models`：数据库表映射
- `tasks`：后台任务

各层职责固定如下：

### 4.1 api

- 接收请求
- 调用 service
- 返回响应

禁止事项：

- 不写复杂业务规则
- 不直接写复杂数据库查询
- 不直接跨模块操作其他模块的数据层

### 4.2 schemas

- 定义请求模型
- 定义响应模型
- 定义模块内公开的数据结构

禁止事项：

- 不承载业务逻辑
- 不直接依赖数据库会话

### 4.3 services

- 承担业务规则
- 组织模块内部用例
- 负责跨模块协作入口

禁止事项：

- 不处理 HTTP 细节
- 不直接暴露数据库实现细节

### 4.4 repositories

- 封装数据库查询
- 封装增删改查
- 封装聚合、筛选、联表、分页

禁止事项：

- 不做业务决策
- 不跨模块写入其他模块的数据

### 4.5 models

- 只定义表结构和关系

禁止事项：

- 不写复杂业务方法
- 不写流程编排逻辑

### 4.6 tasks

- 执行定时任务
- 触发提醒、超时释放、违约记录等后台流程

禁止事项：

- 不重复实现已有业务规则
- 必须调用 service，而不是直接拼装数据库逻辑

## 5. 一级模块

### 5.1 identity

职责：

- 用户信息
- 登录认证
- 院系归属
- 角色权限
- 菜单权限判断

覆盖故事：

- US-09
- US-17
- US-18
- US-19
- US-25

### 5.2 resource

职责：

- 自习室管理
- 座位管理
- 开放时间管理
- 座位属性管理

覆盖故事：

- US-01
- US-02
- US-07
- US-11
- US-12

### 5.3 reservation

职责：

- 创建预约
- 取消预约
- 代预约与代取消
- 历史预约查询
- 冲突校验
- 预约规则校验

覆盖故事：

- US-03
- US-08
- US-10
- US-15

### 5.4 checkin

职责：

- 动态码生成
- 二维码签到
- 签到校验
- 签到状态更新

覆盖故事：

- US-04
- US-23

### 5.5 violation

职责：

- 违约记录生成
- 违约记录查询
- 违约统计基础能力

覆盖故事：

- US-06
- US-14
- US-16

### 5.6 notification

职责：

- 预约前提醒
- 未签到提醒
- 自动取消后的通知

覆盖故事：

- US-05
- US-06

### 5.7 system_config

职责：

- 系统参数
- 最大预约时长
- 签到宽限时间
- 违约判定参数

覆盖故事：

- US-13

### 5.8 assistant

职责：

- 自然语言意图识别
- 查询类请求转发
- 调用内部查询服务

覆盖故事：

- US-20
- US-21
- US-22

### 5.9 admin_portal

职责：

- 管理端页面
- 管理端表单
- 管理端菜单

约束：

- 只做界面适配
- 不承载核心业务规则

## 6. 模块依赖规则

允许依赖：

- `reservation` -> `identity`
- `reservation` -> `resource`
- `reservation` -> `system_config`
- `reservation` -> `violation`（仅限公开只读 service，用于预约前惩罚资格判断）
- `checkin` -> `reservation`
- `checkin` -> `resource`
- `checkin` -> `system_config`
- `violation` -> `reservation`
- `violation` -> `system_config`
- `notification` -> `reservation`
- `notification` -> `checkin`
- `notification` -> `violation`
- `assistant` -> `resource`
- `assistant` -> `reservation`
- `admin_portal` -> 各模块公开 service

禁止依赖：

- `identity` 不依赖业务模块
- `resource` 不依赖 `reservation`
- `models` 不跨模块直接引用业务逻辑
- `repositories` 不跨模块直接写入数据
- `admin_portal` 不直接操作 `repositories`
- `admin_portal` 执行角色停用或删除时，只能调用 `identity` 公开 service，不得直接操作 `identity` repository 或 model
- `api` 不直接操作其他模块的 `models`

跨模块协作规则：

- 只能通过对方模块的 service 层进入
- 不允许直接调用对方 repository
- 不允许直接修改对方 model 状态
- `reservation` 读取 `violation` 时只能消费惩罚资格公开只读 service，不得生成或修改违约记录
- `violation` 读取 `system_config` 时只能通过公开配置读取 service 获取违约累计与惩罚参数

## 7. 业务主线

本项目围绕预约生命周期组织：

`可预约 -> 已预约 -> 已签到 / 超时未签到 -> 自动取消 -> 记录违约`

系统设计必须围绕这条主线展开，不能按页面堆功能。

所有涉及预约状态变化的逻辑，只能由以下模块负责：

- `reservation`
- `checkin`
- `violation`
- `notification`

其中：

- `reservation` 负责预约建立和取消
- `checkin` 负责签到确认
- `violation` 负责违约落账
- `notification` 负责提醒触发

## 8. 目录结构

代码目录固定如下：

```text
app/
  main.py
  core/
    config.py
    database.py
    security.py
  modules/
    identity/
      api/
      models/
      schemas/
      repositories/
      services/
    resource/
      api/
      models/
      schemas/
      repositories/
      services/
    reservation/
      api/
      models/
      schemas/
      repositories/
      services/
    checkin/
      api/
      models/
      schemas/
      repositories/
      services/
    violation/
      api/
      models/
      schemas/
      repositories/
      services/
    notification/
      tasks/
      services/
    system_config/
      api/
      models/
      schemas/
      repositories/
      services/
    assistant/
      api/
      schemas/
      services/
  templates/
  tests/
```

目录约束如下：

- 每个模块自包含
- 共享能力只放 `core`
- 不建立跨模块公共大杂烩目录
- 不建立超深层目录结构

## 9. 设计约束

### 9.1 扁平化

- 模块层级保持简单
- 文件职责保持单一
- 一个文件只解决一类问题

### 9.2 组合优于继承

- 业务对象通过 service 组合协作
- 非必要不建立抽象父类
- 非必要不建立多层基类

允许的继承只限于：

- 框架基础类
- ORM 基类
- 明确必要的少量公共基类

### 9.3 查询优先在数据库完成

- 筛选在查询层完成
- 联表在查询层完成
- 聚合在查询层完成
- 分页在查询层完成

禁止把大量数据取到内存后再做复杂过滤和联结。

### 9.4 明确边界

- 配置规则归 `system_config`
- 权限规则归 `identity`
- 资源规则归 `resource`
- 预约规则归 `reservation`
- 签到规则归 `checkin`
- 违约规则归 `violation`
- 提醒规则归 `notification`

## 10. 单元交付顺序

开发顺序固定如下：

1. `identity`
2. `resource`
3. `system_config`
4. `reservation`
5. `checkin`
6. `violation`
7. `notification`
8. `admin_portal`
9. `assistant`

每个模块交付时必须具备：

- 数据模型
- service
- api
- 基础测试

没有完成最小闭环的模块，不进入下一个模块。

## 11. 变更规则

需求变更时必须遵循以下规则：

1. 先改用户故事
2. 再改本文件
3. 再改代码
4. 再改测试

如果变更涉及跨模块影响，必须先确认三件事：

- 模块职责是否变化
- 模块依赖是否变化
- 业务主线是否变化

未完成这一步，不进入代码修改。
