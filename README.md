# 自习座位预约系统

## 云端网站

- 管理端入口：`http://113.44.135.38:8000/admin/login`
- 健康检查：`http://113.44.135.38:8000/health`

## 登录账号

- 账号：`admin`
- 密码：`admin`

## 云服务器安装步骤

```bash
# 1. 安装 Docker 和 Docker Compose
apt update
apt install -y ca-certificates curl git
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.asc] https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo ${UBUNTU_CODENAME:-$VERSION_CODENAME}) stable" > /etc/apt/sources.list.d/docker.list
apt update
apt install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin

# 2. 拉取项目
mkdir -p /opt
cd /opt
git clone https://github.com/molanyu/26_SPM.git spm
cd /opt/spm

# 3. 准备环境变量
cp .env.example .env

# 4. 启动服务
docker compose up -d --build
```

## 后续云端更新

本地代码和 `dataset/spm_postgres_dump.sql` 推送到 GitHub 后，在云服务器执行：

```bash
cd /opt/spm
bash scripts/huawei_cloud_update.sh
```

