# TASK-003 包仓库适配器（npm / PyPI）

| 项 | 内容 |
|---|---|
| 编号 | TASK-003 |
| 模块 | collect |
| 优先级 | P1 |
| 依赖 | TASK-002（复用 SourceAdapter）|
| 状态 | ⬜ 待开始 |

## 目标
实现 `NpmAdapter`、`PypiAdapter`，按 `candidate_packages` / 关键词查包，并尽量回链到其 GitHub 仓库。

## 实现要点
- npm registry / PyPI JSON API，无需鉴权。
- 包元数据里抽取 repository url，便于后续与 GitHub 结果归并（TASK-005）。
- 输出统一 Candidate，`source` 填 `npm`/`pypi`。

## 验收标准（DoD）
- [ ] 两个适配器都实现 SourceAdapter 协议
- [ ] 能从包元数据解析出仓库地址（拿不到填 null）
- [ ] 输出符合 Candidate 规范
- [ ] 有最小测试
