# TASK-009 Skill 封装（MVP 入口）

| 项 | 内容 |
|---|---|
| 编号 | TASK-009 |
| 模块 | interface |
| 优先级 | P0（MVP 入口）|
| 依赖 | TASK-008（引擎 CLI 跑通）|
| 状态 | ✅ 完成（2026-06-30） |

## 目标
把核心引擎封装成一个 Claude Skill，让用户在 Claude Code 里直接：
「帮我做个文档问答知识库的选型」→ 自动跑全链路 → 返回 Markdown + HTML 报告。

## 实现要点（对应 ADR-007 / ADR-008 / ADR-005 修订）
- **LLM 步骤由宿主 agent 做，skill 不指定 provider、不要 key**：
  - SKILL.md 内置《意图拆解Schema》的指令，让宿主 agent 把用户需求拆成 IntentSpec JSON；
  - agent 把 JSON 交给引擎 `load_intent_spec()` → 跑确定性链路；
  - 评级理由 / 组合建议也由宿主 agent 基于引擎算出的数值与数据来写。
- Skill 做**薄编排**：引导 agent 完成上述步骤 + 调引擎脚本 + 回传报告路径与摘要。
- **支持自定义信源**：用户可在对话里追加"也扫这几个站：URL…"，作为运行时自定义源传给引擎（ADR-008）。
- LLM 无需 key（用宿主 agent）；`GITHUB_TOKEN` 建议配（仅为 GitHub 限流，非 LLM）。
- 引擎本身**不得**依赖 Skill 环境（必须能 `python -m` 独立跑）。
- Skill 描述（description）写清触发场景：开源选型 / 技术调研 / "有没有现成的轮子"。

## 验收标准（DoD）
- [ ] 一句自然语言需求即可触发完整链路并产出报告
- [ ] 能接收并合并用户自定义信源（URL/RSS），报告中展示本次用到的自定义源
- [ ] 报告同时给 Markdown + HTML，路径返回给用户
- [ ] 缺 key / 单源失败有清晰提示，不崩
- [ ] 引擎可脱离 Skill 单独运行（回归验证 TASK-008）
- [ ] Skill 有 README/使用说明
