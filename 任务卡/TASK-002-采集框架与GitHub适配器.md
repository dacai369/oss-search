# TASK-002 采集框架 + GitHub 适配器

| 项 | 内容 |
|---|---|
| 编号 | TASK-002 |
| 模块 | collect |
| 优先级 | P0 |
| 依赖 | TASK-001（用 IntentSpec）|
| 状态 | ✅ 完成（2026-06-30） |

## 范围（已收窄 · 2026-06-30）
本卡**只做单源闭环**，把链路第一段跑通即可，避免一次性铺大：
- ✅ 本卡内：`SourceAdapter` 协议 + `GitHubAdapter` + 查询扩展（关键词/topic 组合）+ 限流/错误处理。
- ❌ 不在本卡：并行采集、多源（npm/PyPI 在 TASK-003、内容源在 TASK-004）、复杂缓存。
  - 先**同步串行**单源；并行与缓存等真有性能/限流瓶颈时再单开卡。

## 目标
1. 定义可插拔 `SourceAdapter` 协议（见 [技术规范.md §5](../规范/技术规范.md)）。
2. 实现 `GitHubAdapter`，按能力关键词/topic 做查询扩展并搜索仓库，输出统一 Candidate。

## 实现要点
- 读取 [信源清单.yaml](../规范/信源清单.yaml)，**本卡只跑 github 这一个** `enabled:true` 源。
- **查询扩展**：每个 capability 用 `keywords_en` + `candidate_topics` 组合成若干查询（如 `topic:` 限定 + 关键词），去重后逐条查。
- GitHub 用 search API；**同步串行**，不做并行/缓存。
- 处理限流：带可选 `GITHUB_TOKEN`、读 `X-RateLimit-*`、退避重试；失败（限流/网络/单查询出错）降级跳过而非崩溃。
- 字段缺失填 `null`，不伪造（见 [Candidate 规范](../规范/技术规范.md#42-candidate候选项目采集层统一输出)）。

## 验收标准（DoD）
- [x] `SourceAdapter` 协议落地，新增源只需实现该协议（接口同 §5）
- [x] GitHubAdapter 输入一个 Capability 能返回 ≥10 条合规 Candidate
- [x] 查询扩展生效：一个能力可生成 ≥2 条去重后的查询
- [x] 输出结构 100% 符合 Candidate 契约（字段齐全，缺失填 `null`）
- [x] 限流/单查询失败有退避重试且不崩（可注入假响应验证）
- [x] 有针对 1 个真实能力的集成测试（**录制响应**离线跑，不连网）
- [x] 引擎可 `python -m oss_search`/独立调用，不依赖 Skill 环境
