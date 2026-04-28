# Runtime Facts

## 1. 文档定位

本文件记录当前项目的运行态事实。

本文件只保存以下内容：

- 当前默认运行环境
- 当前数据库连接与端口
- 当前服务入口地址
- 当前可用演示账号
- 当前运行库中的关键基础数据

本文件不是 architecture 文档，不定义业务边界。
本文件的作用是让顶层窗口、验收窗口和人工操作时快速知道“当前项目怎么启动、连到哪里、用什么账号进入”。

## 2. 当前默认运行环境

当前默认本地运行环境如下：

- 后端运行地址：`http://127.0.0.1:8000`
- 管理端浏览器入口：`http://127.0.0.1:8000/admin/login`
- 健康检查入口：`http://127.0.0.1:8000/health`
- 本地 PostgreSQL 地址：`127.0.0.1:5432`
- Docker Compose 数据库服务名：`db`

当前宿主机局域网 IPv4：

- `192.168.93.206`

说明：

- 浏览器本机访问优先使用 `127.0.0.1`
- 微信开发者工具本地联调可改用 `192.168.93.206:8000`

## 3. 当前数据库配置

当前默认数据库连接配置：

- `DATABASE_URL=postgresql+psycopg://spm:spm@127.0.0.1:5432/spm`
- `POSTGRES_REGRESSION_URL=postgresql+psycopg://spm:spm@127.0.0.1:5432/spm`
- `DATABASE_AUTO_CREATE=false`

当前 Docker Compose 相关配置：

- `DOCKER_DATABASE_URL=postgresql+psycopg://spm:spm@db:5432/spm`
- `POSTGRES_DB=spm`
- `POSTGRES_USER=spm`
- `POSTGRES_PASSWORD=spm`
- `POSTGRES_PORT=5432`
- `APP_PORT=8000`

说明：

- 当前本地默认运行库为 PostgreSQL，而不是 SQLite
- 当前数据库名为 `spm`
- Alembic 迁移已用于 PostgreSQL 建表

## 4. 当前可用账号

### 4.1 管理员账号

当前已写入运行库的管理员账号：

- 登录入口：`/admin/login`
- 账号：`admin`
- 密码：`admin`

说明：

- 当前管理员浏览器登录页输入框已允许使用普通文本账号
- 当前管理员会话使用现有 admin session 机制

### 4.2 学生账号

当前已写入运行库的学生账号：

- 学号：`PGc9b4779b`
- 密码：`student-pass`

说明：

- `20240001 / student-pass` 是测试夹具样例，不是当前运行库里的真实账号
- 小程序联调时应优先使用本节列出的真实学生账号

## 5. 当前运行库中的关键基础数据

当前数据库中已确认存在：

### 5.1 Departments

- `departments.id = 1`
- `name = Postgres Department c9b4779b`
- `code = PGC9B4779B`

当前只确认存在一个 department：

- `id = 1`

说明：

- 管理端创建自习室时，如果直接填写不存在的 `department_id`，会触发外键错误
- 当前运行库下安全可用的 `department_id` 是 `1`

### 5.2 Users

- 学生用户：
  - `id = 1`
  - `student_no = PGc9b4779b`
  - `name = Postgres Student`
  - `department_id = 1`
- 管理员用户：
  - `id = 2`
  - `email = admin`
  - `name = admin`

## 6. 当前小程序配置事实

当前小程序后端地址配置文件：

- `miniprogram/utils/config.js`

当前默认值：

- `http://127.0.0.1:8000`

联调说明：

- 如微信开发者工具无法访问本机 `127.0.0.1`
- 可将 `baseUrl` 临时改为：
  - `http://192.168.93.206:8000`

## 7. 当前环境验证入口

### 7.1 健康检查

- `GET /health`

### 7.2 PostgreSQL 验收脚本

- `scripts/run_postgres_acceptance.ps1`

### 7.3 管理端入口

- `GET /admin/login`

### 7.4 学生端入口

- 微信开发者工具打开 `miniprogram/`

## 8. 顶层窗口读取规则

当问题涉及以下任一类内容时，顶层窗口必须优先读取本文件：

- 环境配置
- 数据库连接
- 端口与入口地址
- 管理员或学生账号
- 小程序联调
- PostgreSQL / Docker / 验收
- 当前运行库数据是否存在

如本文件与真实代码、真实数据库状态冲突，以真实状态为准，并应及时回写本文件。

## 9. 更新规则

出现以下情况时，应更新本文件：

- 默认连接串变化
- 默认端口变化
- 演示账号变化
- Bootstrap 管理员方案变化
- 当前运行库基础数据变化
- 小程序联调地址变化

本文件应保持简短，只保存“当前窗口和人工操作必须知道的运行事实”。
