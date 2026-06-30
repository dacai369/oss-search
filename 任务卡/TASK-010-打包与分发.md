# TASK-010 打包与分发

| 项 | 内容 |
|---|---|
| 编号 | TASK-010 |
| 模块 | release |
| 优先级 | P1（对外发布前必做）|
| 依赖 | TASK-009 |
| 状态 | ⬜ 待开始 |

## 目标
把 skill + 引擎打成可分发的 GitHub 仓库，让别人尽量接近"一键安装即用"（对应 ADR-009）。

## 实现要点
- 仓库结构：`SKILL.md` + 引擎源码 + `pyproject.toml`/安装脚本 + README。
- **首次配置向导**：LLM 由宿主 agent 提供**无需填 key**；仅检测并引导填 `GITHUB_TOKEN`（建议，仅 GitHub 限流用）；`LLM_*` 兜底变量为可选（脱离 agent 单跑时才需，见 ADR-005）。
- README 写清三种安装路径：`install-skill`（GitHub→多工具自动转格式）/ npx skills / 手动放入 skills 目录。
- 明确声明前置依赖（Python 3.11+、需 `pip install` 引擎），别让人以为是零配置；同时说明 LLM 不需要 key。

## 验收标准（DoD）
- [ ] 干净环境按 README 走一遍能装好并跑出报告
- [ ] 缺 `GITHUB_TOKEN`/兜底 `LLM_*` 时配置向导给清晰指引（且明确 LLM 默认走宿主 agent、无需 key）
- [ ] 至少验证 1 个第三方工具（如 Cursor 或另一台机器的 Claude Code）能装上
- [ ] README 含示例需求 + 自定义信源用法
