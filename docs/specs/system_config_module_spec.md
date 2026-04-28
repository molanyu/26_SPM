# System Config Module Spec

## 1. 任务定位

本文件定义 `system_config` 模块的实现边界。

本模块是第三交付单元的一部分，负责提供以下基础能力：

- 系统参数查询
- 系统参数更新
- 参数值校验
- 向其他模块提供统一的配置读取入口

## 2. 实现范围

本次实现只包含以下内容：

- `SystemConfig` 数据模型
- 管理端系统参数列表查询
- 管理端系统参数更新
- 参数值类型校验
- 配置读取 service

本次实现不包含以下内容：

- 预约规则本身的判定逻辑
- 签到规则本身的判定逻辑
- 违约生成逻辑
- 提醒任务调度逻辑
- 配置变更审计日志

### 2.1 首批配置项范围

`system_config` 模块首版固定包含以下配置项：

- `max_reservation_hours`
- `checkin_grace_minutes`
- `violation_threshold_minutes`

说明：

- `max_reservation_hours` 用于限制单次预约最大小时数
- `checkin_grace_minutes` 用于签到宽限时间
- `violation_threshold_minutes` 用于超时未签到后的违约判定阈值

如果后续模块需要新增配置项，必须先更新相关 spec，再修改代码。

### 2.2 配置模块边界

- `system_config` 只负责配置值的存储、读取和更新
- `system_config` 不负责解释完整业务流程
- 配置值如何生效，由使用它的业务模块负责
- 配置值缺失、非法或超出允许范围时，必须在 `system_config` 内被拒绝或阻止写入

## 3. 配置规则

配置规则固定如下：

### 3.1 数据规则

- 每个配置项使用唯一的 `config_key`
- 每个配置项必须有 `config_value`
- 每个配置项必须声明 `value_type`
- 每个配置项可选填写 `description`

### 3.2 更新规则

- 只有管理端允许更新系统参数
- 更新时必须按 `value_type` 做校验
- 更新时必须做参数范围校验
- 非法更新不得落库

### 3.3 读取规则

- 其他模块只能通过 `system_config` 的公开 service 读取配置
- 不允许其他模块直接依赖 `system_config` 的 repository
- 不允许在业务模块中硬编码首批配置项的默认业务规则

### 3.4 首批配置项校验规则

- `max_reservation_hours` 必须是正整数
- `checkin_grace_minutes` 必须是非负整数
- `violation_threshold_minutes` 必须是非负整数
- `violation_threshold_minutes` 不得小于 `checkin_grace_minutes`

## 4. 模块边界

- `system_config` 依赖 `identity` 提供的管理端认证与权限能力
- `system_config` 不依赖 `resource`
- `system_config` 不依赖 `reservation`
- `system_config` 不依赖 `checkin`
- `system_config` 不依赖 `violation`
- `system_config` 不依赖 `notification`

跨模块协作规则固定如下：

- `reservation` 通过 `system_config` 公开 service 读取 `max_reservation_hours`
- `checkin` 通过 `system_config` 公开 service 读取 `checkin_grace_minutes`
- `violation` 通过 `system_config` 公开 service 读取 `violation_threshold_minutes`
- `system_config` 不调用其他业务模块做反向校验

## 5. 数据模型范围

本模块使用以下实体：

- `SystemConfig`

本模块必须保证以下数据规则：

- `config_key` 全局唯一
- `config_value` 使用字符串存储
- `value_type` 必须可用于将 `config_value` 转换为业务模块可读值
- `updated_at` 在每次更新时刷新

## 6. 对外接口

本模块实现以下接口：

### 管理端

- `GET /admin/system-configs`
- `PUT /admin/system-configs/{config_key}`

说明：

- `GET /admin/system-configs` 用于返回首批配置项列表
- `PUT /admin/system-configs/{config_key}` 用于更新指定配置项的值

## 7. 代码边界

目录固定如下：

```text
app/modules/system_config/
  api/
  models/
  schemas/
  repositories/
  services/
```

边界规则如下：

- `api` 只接收请求并调用 `services`
- `services` 负责配置读取、配置更新和参数校验
- `repositories` 负责配置查询与写入
- `models` 只定义表结构
- 不允许其他模块直接操作 `system_config` 的 repository

## 8. 文件级实现清单

本模块实现至少包含以下文件：

```text
app/modules/system_config/models/system_config.py

app/modules/system_config/schemas/config.py

app/modules/system_config/repositories/config_repository.py

app/modules/system_config/services/config_service.py
app/modules/system_config/services/config_reader.py

app/modules/system_config/api/admin_system_config.py
```

## 9. 实现顺序

实现顺序固定如下：

1. 建立 `SystemConfig` 数据模型
2. 建立配置 schema
3. 建立配置 repository
4. 建立配置读取与更新 service
5. 建立管理端查询接口
6. 建立管理端更新接口
7. 建立基础测试

未完成前一步，不进入后一步。

## 10. 测试范围

本模块至少覆盖以下测试：

- 管理员可查询系统参数列表
- 管理员可更新 `max_reservation_hours`
- 管理员可更新 `checkin_grace_minutes`
- 管理员可更新 `violation_threshold_minutes`
- 未认证访问系统参数接口失败
- 无权限访问系统参数接口失败
- 非法 `config_key` 更新失败
- 非法类型更新失败
- 非法范围更新失败
- `violation_threshold_minutes < checkin_grace_minutes` 更新失败
- 其他模块可通过公开 service 读取配置值

## 11. 完成标准

`system_config` 模块完成时，必须满足：

- 管理员可以查询系统参数
- 管理员可以更新首批系统参数
- 参数更新校验可用
- 配置读取 service 可供其他模块调用
- 关键配置测试通过
