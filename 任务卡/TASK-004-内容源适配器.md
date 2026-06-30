# TASK-004 内容源适配器（定向白名单）

| 项 | 内容 |
|---|---|
| 编号 | TASK-004 |
| 模块 | collect |
| 优先级 | P2（V2 增量）|
| 依赖 | TASK-002, TASK-005 |
| 状态 | ⬜ 待开始 |

## 目标
按 [信源清单.yaml](../规范/信源清单.yaml) 的 `content_sources` 白名单采集内容，从文章中**抽取被提及的开源项目**并回链到仓库。

## 范围与顺序（对应 ADR-002）
1. **先做 HelloGitHub**（有结构化数据，最易、最相关）验证内容源链路。
2. 再做有 RSS 的源（阮一峰周刊等）。
3. **公众号最后做**：无官方 API，走第三方/RSS 镜像，反爬重，MVP 不启用。

## 实现要点
- 从文章正文中识别 GitHub/Gitee 链接与项目名（提及 → 项目映射，交给 TASK-005 归并）。
- 内容源的 Candidate 用 `source:content`，并带原文链接到 `raw`。
- **通用源适配器 GenericUrlAdapter（ADR-008）**：能吃任意用户传入的 URL/RSS/公众号链接，走同一套"提及→项目"抽取逻辑。内置白名单源与自定义源共用此能力。
- 信源 = `信源清单.yaml` 白名单 ∪ 运行时自定义源（合并去重）。

## 验收标准（DoD）
- [ ] HelloGitHub 源能产出带仓库回链的 Candidate
- [ ] 文章提及的项目能被抽取（≥80% 命中明显的 GitHub 链接）
- [ ] GenericUrlAdapter 能处理任意传入 URL/RSS，产出合规 Candidate
- [ ] 公众号源以 `enabled:false` 留接口，不阻塞 MVP
- [ ] 有最小测试
