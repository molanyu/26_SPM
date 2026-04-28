# Student Mini Program MVP Spec

## 1. 任务定位

本文件定义学生端微信小程序第一版 MVP 的实现边界。

本阶段目标不是新增后端业务模块，而是把当前已收口的学生端能力组织成可演示、可联调的学生端入口。

本阶段只解决以下问题：

- 学生如何登录
- 学生如何查看可见自习室与座位
- 学生如何创建预约与取消预约
- 学生如何查看当前/历史预约
- 学生如何执行签到
- 学生如何使用助手查询

## 2. 实现范围

本阶段只实现以下页面与能力：

- 登录页
- 自习室列表页
- 座位列表与筛选页
- 我的预约页
- 历史预约复用与再次预约交互
- 签到页
- 助手查询页

本阶段允许在现有后端边界内补充学生端所必需的最小接口缺口。

本阶段不实现以下内容：

- 微信开放平台正式登录
- 真机发布配置
- 订阅消息
- 支付、收藏、消息中心
- 复杂状态管理框架
- UI 组件库接入
- 非查询类自然语言操作

### 2.1 页面职责

- 登录页负责学生学号密码登录，并缓存访问令牌
- 自习室列表页负责查询当前学生可见自习室，并作为学生端主入口
- 座位页负责展示指定自习室座位、属性筛选与创建预约
- 我的预约页负责展示当前有效预约和历史预约，并支持主动取消与再次预约
- 签到页负责动态码签到和二维码签到
- 助手页负责自然语言查询入口与结果展示

### 2.2 后端接口依赖

学生端第一版只允许依赖以下接口：

- `POST /student/auth/login`
- `GET /student/me`
- `GET /student/rooms`
- `GET /student/rooms/{room_id}/seats`
- `POST /student/reservations`
- `GET /student/reservations/current`
- `GET /student/reservations/history`
- `POST /student/reservations/{reservation_id}/cancel`
- `POST /student/checkins/code`
- `POST /student/checkins/qrcode`
- `POST /student/assistant/query`

说明：

- 若发现页面实现依赖未落地接口，先更新相关 spec 和 `api_contracts.md`，再补代码
- 不允许为了前端演示临时绕过现有后端边界

## 3. 模块边界

- 小程序只负责页面展示、表单输入、请求发送和结果展示
- 小程序不复制后端业务规则
- 小程序不自行判定预约是否冲突、签到是否有效、违约是否生成
- 小程序不直接拼装数据库语义

固定协作规则如下：

- 认证令牌由小程序本地缓存
- 认证失败时，小程序清理缓存并跳回登录页
- 页面间通过简单路由参数和本地缓存传递必要上下文
- 不引入全局状态管理框架

## 4. 代码边界

学生端代码目录固定如下：

```text
miniprogram/
  app.js
  app.json
  app.wxss
  project.config.json
  sitemap.json
  utils/
  pages/
```

边界规则如下：

- `utils` 只负责请求封装、鉴权缓存、时间格式化等通用能力
- `pages` 只负责页面逻辑
- 不把多个页面的逻辑堆到单一文件
- 不引入与当前 MVP 无关的页面或组件

## 5. 交互规则

- 登录成功后默认进入自习室列表页
- 自习室列表页必须能跳转到座位页、我的预约页、签到页和助手页
- 座位页必须支持日期、时间和属性筛选
- 创建预约时必须显式提交 `seat_id`、`start_time`、`end_time`
- 我的预约页必须区分当前有效预约和历史预约
- 当前有效预约页项必须支持取消操作
- 历史预约页项必须提供“再次预约”入口
- “再次预约”必须复用历史记录中的 `seat_id`、`start_time`、`end_time` 重新调用 `POST /student/reservations`
- 签到页必须支持手动输入动态码和扫码二维码两种入口
- 助手页查询失败时必须展示受控失败结果，不得自行编造答案

## 6. 文件级实现清单

本阶段至少包含以下文件或同等职责文件：

```text
miniprogram/app.js
miniprogram/app.json
miniprogram/app.wxss
miniprogram/project.config.json
miniprogram/sitemap.json

miniprogram/utils/config.js
miniprogram/utils/request.js
miniprogram/utils/session.js
miniprogram/utils/format.js

miniprogram/pages/login/
miniprogram/pages/rooms/
miniprogram/pages/seats/
miniprogram/pages/reservations/
miniprogram/pages/checkin/
miniprogram/pages/assistant/
```

## 7. 测试与验收范围

本阶段至少覆盖以下验证：

- 学生可登录并进入主页面
- 学生可查询自习室列表
- 学生可查询座位并按属性筛选
- 学生可创建预约
- 学生可查看当前有效预约与历史预约
- 学生可通过历史预约再次预约
- 学生可取消当前未开始预约
- 学生可完成动态码签到或二维码签到
- 学生可提交助手查询并获得受控结果

## 8. 完成标准

学生端 MVP 完成时，必须满足：

- 本地可在微信开发者工具打开
- 核心学生链路可演示
- 历史预约可复用为再次预约
- 不依赖新增业务模块
- 与当前学生端接口契约保持一致
