# 常见 QA

## 1. 文档定位

本文件用于沉淀项目交付、演示、账号理解、权限模型和后台使用中的高频问题。

它面向的是：

- 课程作业阅读者
- 演示观看者
- 本项目的人工使用者

本文件的目标是用尽量直白的方式解释“系统现在是怎么工作的”，帮助读者快速建立正确理解。

本文件不替代以下正式文档：

- 模块 spec
- API 契约
- 数据模型
- 交付与运行说明

如本文件与正式 spec 或真实代码不一致，以正式 spec 和真实代码为准，并应及时回写本文件。

## 2. 账号、角色与权限

### Q1. 学生账户是不是角色？现在系统是不是只有 admin 一个角色？

不是。

当前项目里，`学生` 和 `管理员` 首先都是统一的 `User` 账号实体，不是靠“用户类型字段”或“学生角色”来区分。

可以先这样理解：

- `User` 是账号本体
- `Role` 是权限包
- `Permission` 是最小权限点
- 学生端登录依赖 `student_no + password`
- 管理端登录依赖 `email + password`
- 管理员想进入后台，还必须通过 `Role -> Permission` 间接拥有 `admin.portal.access`

因此：

- 学生账号不是一个叫“student”的角色
- 学生即使当前 `0 个角色`，也仍然可以正常登录学生端
- 角色主要用于后台管理权限控制

当前真实实现里，系统默认/自动创建的角色基本只有一个：

- `system_admin`

但这不代表系统只能有一个角色。当前实现本身支持：

- 创建多个角色
- 给角色配置多个权限点
- 把角色分配给用户

只是目前已落地的权限点主要围绕管理端能力，例如：

- `admin.portal.access`
- `identity.roles.read`
- `identity.roles.write`
- `identity.permissions.read`
- `identity.users.roles.write`

可以用下面这张简化关系图理解：

```text
User
├─ 可选关联 Department
├─ 学生登录：student_no + password
├─ 管理员登录：email + password
└─ 可分配 0..n 个 Role

Role
└─ 可关联 0..n 个 Permission

Permission
└─ 定义具体能力点，例如 admin.portal.access
```

登录链路可以再压缩成两句话：

```text
学生登录：
  按 student_no 查 User -> 校验密码 -> 签发 student token

管理员登录：
  按 email 查 User -> 校验密码 -> 检查是否拥有 admin.portal.access -> 创建 admin session
```

所以，当你在“用户角色分配”页面里看到某个学生当前 `0 项角色` 时，这通常是正常现象，不表示该学生账号无效；它只表示这个学生目前没有被授予后台管理相关角色。

参考来源：

- `docs/specs/identity_module_spec.md`
- `docs/architecture/data_model.md`
- `app/modules/identity/models/user.py`
- `app/modules/identity/services/auth_service.py`
- `app/modules/identity/services/permission_service.py`
- `app/modules/identity/constants.py`
