# Dataset Backup

本目录用于保存本地运行库导出的 PostgreSQL 数据备份。

当前备份文件：

- `spm_postgres_dump.sql`

## 云服务器恢复方式

在云服务器项目目录执行：

```bash
cd /opt/spm
git pull
docker cp dataset/spm_postgres_dump.sql spm-db-1:/tmp/spm_postgres_dump.sql
docker exec -i spm-db-1 psql -U spm -d spm -f /tmp/spm_postgres_dump.sql
docker compose restart api
```

恢复完成后访问：

```text
http://113.44.135.38:8000/admin/login
```

使用本地数据库中的管理员账号登录。
