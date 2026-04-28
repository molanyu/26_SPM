# 技术选型

## 最终方案

- 后端：`FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2`
- 管理端：`Jinja2 + HTMX + 少量原生 JavaScript`
- 数据库：`PostgreSQL`
- 定时任务：`APScheduler`
- 测试：`pytest`
- 部署：`Docker + Docker Compose`

## 选型原则

- 优先 AI 友好，而不是最少样板代码
- 优先代码可读性和边界清晰，而不是框架能力堆叠
- 优先模块化单体和快速交付，而不是复杂架构

## 后端

后端采用 `FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2`。

选择这套方案的原因是：

- 接口层、数据模型、业务逻辑可以清晰分层
- 查询逻辑显式，适合复杂筛选、联表和聚合
- 对 AI 更友好，便于持续生成和维护代码
- 容器化和测试接入都比较直接

不采用 `SQLModel` 作为最终方案，原因是它虽然更省样板代码，但模型边界不如 `SQLAlchemy + Pydantic` 清楚。本项目更看重长期可读性和 AI 协作稳定性。

## 管理端

管理端采用 `Jinja2 + HTMX + 少量原生 JavaScript`，不做重型前后端分离。

选择这套方案的原因是：

- 管理端主要是 CRUD、筛选、查询和配置
- 页面结构简单，更适合快速实现
- 文件更少，AI 更容易维护上下文
- 开发、联调和部署成本更低

## 数据库

数据库采用 `PostgreSQL`。

选择原因是：

- 本项目是典型关系型业务系统
- 需要事务、约束、关联查询和统计能力
- 与 `SQLAlchemy 2.0` 配合成熟
- 更适合后续容器化部署

## 定时任务

定时任务采用 `APScheduler`。

选择原因是：

- 当前任务规则固定，复杂度不高
- 配置简单，便于本地调试
- 不需要引入更重的异步任务体系

## 测试与部署

- 测试采用 `pytest`
- 部署采用 `Docker + Docker Compose`

这套组合便于接入自动化测试、持续集成和云端容器部署，也符合课程项目对 DevOps 流程的要求。

## 结论

本项目最终技术路线以“AI 友好、结构清晰、代码简单、易于交付”为第一优先级，因此采用：

`FastAPI + SQLAlchemy 2.0 + Alembic + Pydantic v2 + PostgreSQL + Jinja2/HTMX + APScheduler + pytest + Docker Compose`
