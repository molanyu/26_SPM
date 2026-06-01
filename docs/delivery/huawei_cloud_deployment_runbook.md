# 华为云服务器部署运行手册

## 1. 文档定位

本文档记录本项目在华为云 Flexus 云服务器上已经验证成功的部署流程。

本文档用于之后重新创建云服务器、拉取代码、启动后端、恢复本地数据库并联调微信开发者工具。

本文档不覆盖正式生产发布、域名备案、HTTPS 证书、CI/CD 自动部署或云数据库托管。

## 2. 已验证环境

本次成功部署使用的服务器配置如下：

- 云厂商：华为云
- 实例类型：Flexus 云服务器 X 实例
- 区域：华北-北京四
- 规格：`2 vCPU / 6 GiB`
- 操作系统：`Ubuntu 22.04 server 64bit`
- 系统盘：`40 GiB`
- 公网 IP：`113.44.135.38`
- 后端端口：`8000`
- 数据库：同机 Docker PostgreSQL 16

安全组临时调试需要开放：

- `TCP 22`：SSH / CloudShell 登录
- `TCP 8000`：临时访问 FastAPI / 管理端
- `TCP 80`：后续 Nginx 反向代理可用
- `TCP 443`：后续 HTTPS 可用

注意：

- 不要在安全组开放 `TCP 5432` 给公网。
- 当前 `docker-compose.yml` 会把 PostgreSQL 映射到宿主机 `5432`，但只要安全组不开放 `5432`，公网无法直接访问。

## 3. 购买服务器参数

购买时选择：

- 镜像：`Ubuntu 22.04 server 64bit`
- CPU / 内存：最低 `2 vCPU / 2 GiB`，推荐 `2 vCPU / 4 GiB` 以上，本次使用 `2 vCPU / 6 GiB`
- 系统盘：最低 `40 GiB`
- 弹性公网 IP：现在购买
- 线路：全动态 BGP
- 公网带宽计费：按带宽计费
- 带宽：`2 Mbps` 可用于课程演示
- VPC / 子网：默认即可
- 安全组：可使用 WebServer 类安全组，后续确认端口规则

微信开发者工具不安装在云服务器上。

- 云服务器负责运行后端、管理端网页、PostgreSQL。
- Windows 本机负责运行微信开发者工具和浏览器。

## 4. 登录服务器

在华为云控制台进入 Flexus 云服务器实例，点击远程登录。

CloudShell 登录参数：

- IP：选择公网 IP
- 端口：`22`
- 用户名：`root`
- 认证方式：密码认证
- 密码：创建服务器时设置的 root 密码

登录成功后应看到：

```bash
root@flexusx-eb41:~#
```

## 5. 安装 Docker 与 Git

服务器首次初始化后执行：

```bash
apt update
apt install -y ca-certificates curl gnupg git

install -m 0755 -d /etc/apt/keyrings

curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc

echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list

apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

systemctl enable --now docker

docker --version
docker compose version
```

本次成功结果示例：

```text
Docker version 29.4.1
Docker Compose version v5.1.3
```

## 6. 配置 Docker 镜像加速

如果拉取 `postgres:16` 或 `python:3.13-slim` 超时，配置镜像加速：

```bash
mkdir -p /etc/docker

cat > /etc/docker/daemon.json <<'EOF'
{
  "registry-mirrors": [
    "https://docker.m.daocloud.io",
    "https://docker.1ms.run",
    "https://registry.cn-hangzhou.aliyuncs.com"
  ]
}
EOF

systemctl daemon-reload
systemctl restart docker
docker info | grep -A 10 "Registry Mirrors"
```

应能看到：

```text
Registry Mirrors:
 https://docker.m.daocloud.io/
 https://docker.1ms.run/
 https://registry.cn-hangzhou.aliyuncs.com/
```

## 7. GitHub 私有仓库 Token

因为仓库是私有仓库，服务器不能使用 GitHub 登录密码拉取。

在 GitHub 创建 Fine-grained token：

- Repository access：Only select repositories
- Repository：`molanyu/26_SPM`
- Contents：Read and write
- Metadata：Read-only

说明：

- 如果服务器只负责 `git clone` 和 `git pull`，`Contents: Read-only` 即可。
- 如果之后需要在服务器上改代码并 `git push`，使用 `Contents: Read and write`。
- Token 只显示一次，生成后立即保存。

## 8. 拉取项目代码

在服务器执行：

```bash
cd /opt
git clone https://github.com/molanyu/26_SPM.git spm
cd /opt/spm
ls
```

提示用户名时输入：

```text
molanyu
```

提示密码时粘贴 GitHub token。

成功后目录为：

```bash
/opt/spm
```

## 9. 修复云端 pip 下载慢问题

本次在构建 Docker 镜像时，`python -m pip install .` 从 PyPI 下载依赖反复超时。

成功处理方式是在云服务器项目目录把 Dockerfile 改为使用清华 PyPI 源：

```bash
cd /opt/spm
python3 - <<'PY'
from pathlib import Path

p = Path("Dockerfile")
s = p.read_text()
s = s.replace(
    "RUN python -m pip install --upgrade pip && \\\n    python -m pip install .",
    "RUN python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple --upgrade pip && \\\n    python -m pip install -i https://pypi.tuna.tsinghua.edu.cn/simple ."
)
p.write_text(s)
PY

grep -n "pip install" Dockerfile
```

说明：

- 这是本次云服务器上验证成功的修复步骤。
- 如果后续把该 Dockerfile 改动提交回 GitHub，新服务器可省略本节。

## 10. 启动容器

在服务器项目目录执行：

```bash
cd /opt/spm
docker compose up -d --build
```

成功结果示例：

```text
Image spm-api Built
Network spm_default Created
Volume spm_postgres_data Created
Container spm-db-1 Healthy
Container spm-api-1 Started
```

查看状态：

```bash
docker compose ps
```

正常应看到：

```text
spm-api-1   Up
spm-db-1    Up (healthy)
```

查看后端日志：

```bash
docker compose logs --tail=100 api
```

正常日志应包含：

```text
Application startup complete.
Uvicorn running on http://0.0.0.0:8000
```

## 11. 健康检查

服务器本机检查：

```bash
curl http://127.0.0.1:8000/health
```

成功返回：

```json
{"status":"ok"}
```

浏览器公网检查：

```text
http://113.44.135.38:8000/health
```

如果浏览器无法访问，确认安全组已经开放：

```text
入方向 TCP 8000 源地址 0.0.0.0/0
```

## 12. 恢复本地 PostgreSQL 数据

当前 GitHub 仓库中 `*.db` 文件是 SQLite 旧文件，不是当前本地正在使用的 PostgreSQL 运行库。

本地 PostgreSQL 运行库已导出到：

```text
dataset/spm_postgres_dump.sql
```

云服务器恢复步骤：

```bash
cd /opt/spm
git pull

docker cp dataset/spm_postgres_dump.sql spm-db-1:/tmp/spm_postgres_dump.sql
docker exec -i spm-db-1 psql -U spm -d spm -f /tmp/spm_postgres_dump.sql
docker compose restart api
```

恢复后可用账号来自本地数据库：

管理员：

```text
入口：http://113.44.135.38:8000/admin/login
账号：admin
密码：admin
```

学生：

```text
学号：PGc9b4779b
密码：student-pass
```

说明：

- 云端第一次启动时数据库是空库，直接使用 `admin / admin` 可能登录失败。
- 恢复 `dataset/spm_postgres_dump.sql` 后，才会拥有本地数据库中的管理员、学生、院系、自习室等数据。

## 12.1 后续一键更新脚本

后续本地代码和 `dataset/spm_postgres_dump.sql` 已经提交并推送到 GitHub 后，云服务器只需要执行：

```bash
cd /opt/spm
bash scripts/huawei_cloud_update.sh
```

脚本会自动完成：

- 从 GitHub 拉取当前分支最新代码
- 拉取 GitHub 时显示 Git 原生进度，并每 15 秒打印一次仍在运行提示
- 启动并等待 PostgreSQL 就绪
- 停止旧 API，避免导入数据库时仍有旧服务连接
- 先备份当前云端数据库到 `backups/cloud-db/`
- 自动导入 `dataset/spm_postgres_dump.sql`
- 重新构建并启动 Docker Compose 服务
- 检查 `/health`
- 打印容器状态和最近 API 日志

如果本次只更新代码，不想覆盖云端数据库：

```bash
cd /opt/spm
bash scripts/huawei_cloud_update.sh --skip-db
```

如果服务器项目目录不是 `/opt/spm`：

```bash
bash /实际项目目录/scripts/huawei_cloud_update.sh --app-dir /实际项目目录
```

如果希望进度提示更频繁，例如每 5 秒打印一次：

```bash
cd /opt/spm
PROGRESS_INTERVAL_SECONDS=5 bash scripts/huawei_cloud_update.sh
```

## 13. 管理端访问

临时调试访问：

```text
http://113.44.135.38:8000/admin/login
```

登录：

```text
账号：admin
密码：admin
```

说明：

- `:8000` 是临时调试端口。
- 正式访问建议后续增加 Nginx，把公网 `80` 转发到本机 `8000`。

## 14. 微信开发者工具联调

微信开发者工具仍在 Windows 本机运行。

修改小程序配置：

```text
miniprogram/utils/config.js
```

将：

```js
const baseUrl = 'http://127.0.0.1:8000'
```

改为：

```js
const baseUrl = 'http://113.44.135.38:8000'

module.exports = {
  baseUrl,
}
```

微信开发者工具设置：

1. 打开 `miniprogram/`
2. 点击右上角“详情”
3. 进入“本地设置”
4. 勾选“不校验合法域名、web-view、TLS 版本以及 HTTPS 证书”
5. 编译运行

学生端登录：

```text
学号：PGc9b4779b
密码：student-pass
```

说明：

- `http://公网IP:8000` 只适合微信开发者工具调试。
- 真机预览或上线通常需要 HTTPS、已备案域名和小程序 request 合法域名配置。

## 15. 常见问题

### 15.1 SSH 登录提示端口未开放

先检查安全组入方向是否存在：

```text
TCP 22
源地址 0.0.0.0/0
```

如果规则已存在但仍提示，可等待 1 分钟刷新，或直接尝试 CloudShell 登录。

### 15.2 Docker Hub 拉镜像超时

错误示例：

```text
failed to resolve reference "docker.io/library/postgres:16"
i/o timeout
```

处理方式：

1. 先配置 Docker 镜像加速。
2. 再执行 `docker compose up -d --build`。

### 15.3 pip 下载依赖超时

错误现象：

```text
WARNING: Connection timed out while downloading.
```

处理方式：

- 修改 Dockerfile 使用清华 PyPI 源。
- 再重新执行 `docker compose up -d --build`。

### 15.4 管理员登录失败

原因：

- 云端数据库是新库，没有本地已有账号。
- 或者还没有恢复 `dataset/spm_postgres_dump.sql`。

处理方式：

```bash
cd /opt/spm
git pull
docker cp dataset/spm_postgres_dump.sql spm-db-1:/tmp/spm_postgres_dump.sql
docker exec -i spm-db-1 psql -U spm -d spm -f /tmp/spm_postgres_dump.sql
docker compose restart api
```

### 15.5 GitHub 私有仓库 clone 失败

错误示例：

```text
Password authentication is not supported for Git operations.
```

处理方式：

- 用户名输入 GitHub 用户名。
- 密码位置输入 GitHub token，不是 GitHub 登录密码。

### 15.6 GitHub pull 出现 GnuTLS recv error

错误示例：

```text
fatal: unable to access 'https://github.com/molanyu/26_SPM.git/': GnuTLS recv error (-110): The TLS connection was non-properly terminated.
```

这是云服务器到 GitHub 的 HTTPS 连接被中途断开，通常是临时网络抖动或 Git HTTP/2/GnuTLS 兼容性问题。

优先重新执行一键更新脚本。脚本已内置 `git fetch` / `git pull` 重试，并强制 Git 使用 HTTP/1.1。

如果仍失败，可以先在云服务器执行：

```bash
git config --global http.version HTTP/1.1
git config --global http.lowSpeedLimit 0
git config --global http.lowSpeedTime 999999

cd /opt/spm
bash scripts/huawei_cloud_update.sh
```

如果连续多次失败，等待几分钟后重试，或把远程地址改为 SSH 方式再拉取。

## 16. 后续建议

当前流程已经满足课程演示和云端调试。

后续如需更接近正式部署，建议逐步完成：

- 使用 Nginx 将 `80` 转发到 `127.0.0.1:8000`
- 关闭安全组中的 `8000` 公网入口，只保留 `80/443/22`
- 修改 `docker-compose.yml`，去掉 PostgreSQL 的宿主机端口映射
- 配置域名、备案和 HTTPS
- 小程序配置正式 request 合法域名
- 将云端 Dockerfile 的清华 PyPI 源改动提交回 GitHub
