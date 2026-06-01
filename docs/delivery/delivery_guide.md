# Delivery Guide

## 1. 文档定位

本文档用于课程交付前的最小运行说明。

本文档只回答以下问题：

- 如何本地启动后端
- 如何通过容器启动后端
- 如何初始化管理员
- 如何打开学生端小程序
- 如何按固定脚本演示项目

## 2. 本地启动

### 2.1 安装依赖

```bash
python -m pip install -e .[test]
```

### 2.2 本地数据库方式

轻量开发和当前主测试链路仍可使用默认 SQLite。

```bash
uvicorn app.main:app --reload
```

如果要切换到 PostgreSQL，请先复制 `.env.example` 为 `.env`，并设置：

- `DATABASE_URL`
- `POSTGRES_REGRESSION_URL`
- `DATABASE_AUTO_CREATE=false`

推荐直接执行项目脚本：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_postgres_acceptance.ps1
```

如果你要手动执行命令，必须先把环境变量导入到当前 shell，再执行：

```bash
alembic upgrade head
uvicorn app.main:app --reload
```

如果只想做 PostgreSQL 验收，直接执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_postgres_acceptance.ps1
```

如果本机使用 Docker 启动 PostgreSQL，则执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_postgres_acceptance.ps1 -StartDockerDb
```

对应的最小说明见：

- `docs/delivery/postgresql_acceptance.md`

### 2.3 提交前同步 PostgreSQL 数据快照

如果本地使用 Docker PostgreSQL，并且希望云端更新时同步当前本地数据，提交代码前先执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export_postgres_dump.ps1
```

脚本会从当前 Docker Compose 的 `db` 容器导出 PostgreSQL 数据，覆盖更新：

```text
dataset/spm_postgres_dump.sql
```

然后再提交并推送：

```powershell
git add dataset\spm_postgres_dump.sql
git commit -m "Update PostgreSQL dataset dump"
git push
```

如果希望脚本导出后顺手暂存 dump 文件：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\export_postgres_dump.ps1 -GitAdd
```

## 3. 容器启动

华为云 Flexus 云服务器的完整已验证部署流程见：

- `docs/delivery/huawei_cloud_deployment_runbook.md`

### 3.1 准备环境变量

复制：

```bash
.env.example -> .env
```

按需修改：

- `JWT_SECRET_KEY`
- `IDENTITY_BOOTSTRAP_ENABLED`
- `IDENTITY_BOOTSTRAP_ADMIN_EMAIL`
- `IDENTITY_BOOTSTRAP_ADMIN_PASSWORD`

### 3.2 启动容器

```bash
docker compose up --build
```

容器启动顺序固定为：

1. PostgreSQL 就绪
2. `alembic upgrade head`
3. `uvicorn app.main:app`

## 4. Bootstrap 管理员初始化

如需初始化首个管理员，开启以下变量：

- `IDENTITY_BOOTSTRAP_ENABLED=true`
- `IDENTITY_BOOTSTRAP_ADMIN_EMAIL`
- `IDENTITY_BOOTSTRAP_ADMIN_PASSWORD`

说明：

- bootstrap 是受控初始化
- bootstrap 不是迁移工具
- bootstrap 不负责自动修复 schema
- 当前演示环境不预置固定管理员账号
- 演示环境中的管理员账号默认由上述 bootstrap 变量创建

推荐演示配置示例：

- `IDENTITY_BOOTSTRAP_ENABLED=true`
- `IDENTITY_BOOTSTRAP_ADMIN_EMAIL=admin@example.com`
- `IDENTITY_BOOTSTRAP_ADMIN_PASSWORD=admin-pass`

如需同时展示浏览器后台登录闭环，启动应用后直接使用上述账号访问：

- `GET /admin/login`

首次进入后台的最小步骤固定为：

1. 设置 bootstrap 环境变量
2. 启动应用
3. 浏览器打开 `/admin/login`
4. 使用 bootstrap 管理员邮箱和密码登录
5. 登录成功后进入 `/admin`

## 5. 学生端小程序

学生端目录位于：

- `miniprogram/`

本地调试步骤：

1. 使用微信开发者工具打开 `miniprogram/`
2. 关闭合法域名校验
3. 按实际后端地址修改 `miniprogram/utils/config.js`
4. 登录学生账号后按主链路演示

## 6. 真实邮件通知演示（可选）

如需演示真实邮件提醒，而不是默认 `mock` 通道，请额外配置：

- `NOTIFICATION_DEFAULT_CHANNEL=smtp_email`
- `SMTP_HOST`
- `SMTP_PORT`
- `SMTP_USERNAME`
- `SMTP_PASSWORD`
- `SMTP_FROM_EMAIL`
- `SMTP_USE_TLS`
- `SMTP_TIMEOUT_SECONDS`

说明：

- 推荐使用邮箱服务提供商的授权码或应用专用密码，不要直接使用邮箱网页登录密码
- 默认开发环境、自动化测试和 CI 仍建议使用 `NOTIFICATION_DEFAULT_CHANNEL=mock`
- 被提醒用户必须已有可用 `email` 字段；若目标用户缺少邮箱，系统会受控失败并记录失败日志
- 若 `smtp_email` 所需配置缺失或非法，系统会受控失败并记录失败日志，不会自动回退到 `mock`

## 7. 固定演示路径

建议按以下顺序演示：

1. 浏览器访问 `/admin/login`
2. 使用 bootstrap 管理员账号登录管理端
3. 管理端确认自习室、座位和系统参数
4. 学生端登录
5. 学生端查看自习室与座位
6. 学生端创建预约
7. 学生端查看当前预约
8. 学生端执行签到或演示超时链路
9. 管理端查看违约与统计
10. 学生端使用助手查询

## 8. 已知风险

- 主自动化测试链路仍以 SQLite/内存库为主
- PostgreSQL 当前只覆盖 smoke 回归，不是全量双库矩阵
- 小程序第一版使用账号密码登录，不包含正式微信登录
- 小程序默认面向开发者工具调试，未覆盖真机发布配置
