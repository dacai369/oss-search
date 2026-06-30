# TASK-006 质量评级引擎

| 项 | 内容 |
|---|---|
| 编号 | TASK-006 |
| 模块 | score |
| 优先级 | P0 |
| 依赖 | TASK-005 |
| 状态 | ✅ 完成（2026-06-30） |

## 目标
实现 `score(candidates, spec) -> list[ScoredCandidate]`：多维打分 + 加权汇总 + 评级 + 给理由。

## 实现要点
- 维度与权重见 [技术规范.md §6](../规范/技术规范.md)（MVP 初版，权重可配置）。
- `relevance`：需求/能力描述 vs README 的 embedding 相似度。
- 缺失字段降权而非报错（拿不到 contributors 就该维度按中性/低分处理）。
- 每个维度产出一句**人话理由**，写入 `reasons`（这是用户信任的关键）。

## 验收标准（DoD）
- [x] 接口签名与规范一致，输出 ScoredCandidate 结构完整
- [x] 6 个维度都有分，total_score ∈ [0,1]，grade ∈ {A,B,C,D}
- [x] 每个候选至少 3 条可读理由
- [x] 权重可通过配置调整
- [x] 有测试：构造高质量/低质量样本，排序符合预期
