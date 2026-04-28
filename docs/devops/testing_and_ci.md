# Testing And CI

## 1. 文档定位

本文档说明项目第一版 `tests/devops` 收口方案：

- 统一测试命令
- 关键模块自动化测试覆盖范围
- 最小 CI 工作流
- 测试失败阻断规则

本文档不描述部署、发布审批、性能压测或安全扫描集成。

## 2. 统一测试命令

项目统一测试入口为：

```bash
python run_tests.py
```

该命令会执行：

- `tests/test_run_tests.py`
- `tests/identity`
- `tests/resource`
- `tests/system_config`
- `tests/reservation`
- `tests/checkin`
- `tests/violation`
- `tests/notification`
- `tests/assistant`
- `tests/admin_portal`

统一入口固定透传：

- `-q`
- `-p no:cacheprovider`

这样可以保证本地与 CI 复用同一套 pytest 调用参数。

项目还提供一个可选的 PostgreSQL smoke suite：

```bash
python run_tests.py --suite postgres
```

该套件默认不纳入 `all`，用于在真实 PostgreSQL 环境下验证迁移后的核心学生链路。

## 3. 最小测试分层

第一版只建立最小分层：

- `python run_tests.py --suite unit`
  - 运行项目级测试入口自检：`tests/test_run_tests.py`
- `python run_tests.py --suite integration`
  - 运行关键业务模块测试与 `admin_portal` 基础页面/权限测试
- `python run_tests.py --suite postgres`
  - 运行 PostgreSQL smoke 回归测试
- `python run_tests.py`
  - 默认运行 `all`，即 `unit + integration`

说明：

- 关键模块覆盖范围与 `docs/specs/tests_devops_module_spec.md` 保持一致
- `admin_portal` 只纳入基础页面与权限测试，不扩展到完整 UI 自动化

## 4. 本地执行

建议先安装项目与测试依赖：

```bash
python -m pip install -e .[test]
```

然后执行统一命令：

```bash
python run_tests.py
```

如需只验证入口自身或模块测试层，可分别执行：

```bash
python run_tests.py --suite unit
python run_tests.py --suite integration
python run_tests.py --suite postgres
```

## 5. CI 工作流

最小 CI 配置文件位于：

- `.github/workflows/test.yml`

CI 只做三件事：

1. 安装项目与测试依赖
2. 执行统一测试命令 `python run_tests.py`
3. 根据退出码返回成功或失败

此外还存在一条独立的 PostgreSQL smoke job：

1. 启动 PostgreSQL service
2. 执行 `alembic upgrade head`
3. 执行 `python run_tests.py --suite postgres`

CI 不使用与本地不同的隐藏测试逻辑。

## 6. 失败阻断规则

- 任一关键测试失败，`python run_tests.py` 非零退出
- GitHub Actions job 因非零退出码直接失败
- 不使用 `continue-on-error`
- 不通过跳过核心测试伪造绿色流水线

## 7. 第一版范围外

以下能力不在第一版 `tests/devops` 范围内：

- 自动部署到云端
- 蓝绿发布
- 性能压测流水线
- 安全扫描平台接入
- 多环境发布审批流
