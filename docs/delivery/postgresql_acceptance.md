# PostgreSQL Acceptance

## 1. 文档定位

本文档只描述 PostgreSQL 验收。

目标是把 PostgreSQL 验收收敛成：

- 最少的环境准备
- 一条可直接执行的脚本
- 一份极短的人工检查清单

## 2. 自动化入口

统一脚本位于：

- `scripts/run_postgres_acceptance.ps1`

脚本会自动完成以下工作：

1. 如无 `.env`，自动从 `.env.example` 复制生成
2. 读取 `.env`
3. 将 `POSTGRES_REGRESSION_URL` 缺省回落到 `DATABASE_URL`
4. 固定 `DATABASE_AUTO_CREATE=false`
5. 执行 `python -m alembic upgrade head`
6. 执行 `python run_tests.py --suite postgres`

说明：

- `.env` 由该脚本读取并注入当前进程
- 如果你绕过该脚本直接运行 `alembic` 或 `python run_tests.py --suite postgres`，需要先手动导入环境变量

## 3. 使用方式

### 3.1 使用已有 PostgreSQL

只需保证 `.env` 中的以下变量可用：

- `DATABASE_URL`
- `POSTGRES_REGRESSION_URL`

然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_postgres_acceptance.ps1
```

### 3.2 使用 Docker 启动本地 PostgreSQL

只需保证 Docker Desktop 已启动，然后执行：

```powershell
powershell -ExecutionPolicy Bypass -File .\scripts\run_postgres_acceptance.ps1 -StartDockerDb
```

该模式会自动执行：

1. `docker compose up -d db`
2. 等待 PostgreSQL healthy
3. Alembic 迁移
4. PostgreSQL smoke 测试

## 4. 仍需人工操作的部分

脚本之外，仍然需要你人工保证以下条件成立：

1. 本机已安装并可运行 Python 依赖环境
2. 如果使用 Docker 方案，Docker Desktop 已启动
3. 如果使用外部 PostgreSQL，连接串真实可达
4. 课程验收所需的截图或录屏由你人工留痕

## 5. 通过标准

PostgreSQL 验收通过时，应满足：

- Alembic 迁移成功
- `python run_tests.py --suite postgres` 通过
- 日志中可看到学生登录、查询资源、创建预约、查询当前预约这条 smoke 链路完成
