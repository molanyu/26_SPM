# Deployment Baseline Spec

## 1. 任务定位

本文件定义项目进入“可交付运行”阶段时的部署基线。

本阶段目标是把当前仅依赖本地 SQLite 与 `create_all` 的运行方式，提升为可迁移、可容器化、可在 PostgreSQL 上启动的正式基线。

## 2. 实现范围

本阶段只实现以下内容：

- Alembic 迁移体系
- 初始数据库迁移基线
- Dockerfile
- docker-compose.yml
- `.env.example`
- PostgreSQL 真实环境 smoke 回归入口
- 交付说明文档

本阶段不实现以下内容：

- 云端自动部署
- 多环境发布审批
- 蓝绿发布
- 生产级监控告警
- 复杂基础设施编排

### 2.1 数据库初始化规则

- 正式环境默认使用 Alembic 迁移管理数据库结构
- 应用进程本身不承担迁移职责
- 正式环境启动顺序固定为：迁移 -> 启动应用
- `create_all` 只保留给测试和本地轻量开发使用

### 2.2 Bootstrap 规则

- `identity bootstrap` 继续保留
- bootstrap 只负责受控初始化管理员账号和权限
- bootstrap 不负责修库、补迁移、自动修复 schema

## 3. 模块边界

- 迁移基线属于项目级基础设施，不属于任一业务模块
- 迁移文件只描述 schema 变化，不承载业务规则
- 容器文件只负责运行环境，不复制业务逻辑
- PostgreSQL smoke 回归只验证真实环境链路，不替代现有 SQLite 主测试链路

## 4. 代码与资产边界

本阶段主要涉及以下路径：

```text
alembic.ini
alembic/

Dockerfile
docker-compose.yml
.env.example
.dockerignore

docs/devops/
docs/delivery/

tests/postgres/
```

必要时允许补充：

- `app/core/` 下与数据库初始化、模型注册相关的最小支撑代码
- `run_tests.py` 和 CI 工作流中与 PostgreSQL smoke 相关的最小入口

## 5. 测试规则

本阶段必须同时保留两类验证：

- 当前统一测试入口的 SQLite/内存测试链路
- 面向 PostgreSQL 的最小 smoke 回归链路

PostgreSQL smoke 至少验证：

- 迁移可执行
- 应用可启动
- 基本登录可用
- 至少一条核心学生链路可跑通

## 6. 文件级实现清单

本阶段至少包含以下文件或同等职责文件：

```text
alembic.ini
alembic/env.py
alembic/script.py.mako
alembic/versions/

Dockerfile
docker-compose.yml
.env.example
.dockerignore

tests/postgres/
docs/devops/testing_and_ci.md
docs/delivery/delivery_guide.md
```

## 7. 完成标准

部署基线完成时，必须满足：

- PostgreSQL 可通过迁移初始化
- 容器环境可完成迁移并启动应用
- 本地与 CI 都保留统一测试入口
- 存在一条真实 PostgreSQL smoke 回归路径
- 存在可读的本地/容器/初始化说明
