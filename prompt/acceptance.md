请先读取以下真实文档，再进入本轮验收工作：

- docs/requirements/acceptance_matrix.md
- docs/devops/testing_and_ci.md
- docs/delivery/delivery_guide.md
- docs/specs/student_miniprogram_mvp_spec.md
- docs/specs/deployment_baseline_spec.md

当前任务：
执行项目验收与稳定化检查，不新增功能，不重构模块。

本轮目标：
1. 检查当前项目是否满足课程交付的最小验收条件
2. 运行统一测试与部署基线验证
3. 给出“已通过 / 未通过 / 需人工执行”的清单
4. 如果发现问题，只输出问题和修复建议，不直接改代码

验收范围：
- 统一测试入口
- PostgreSQL 迁移与 smoke
- Docker/Compose 启动链路
- 学生端小程序 MVP 是否具备可演示条件
- acceptance_matrix 主线故事是否具备验收基础

输出格式固定为：
- 当前项目验收状态摘要
- 已自动验证通过项
- 需人工执行项
- 未通过项
- 下一步修复建议
