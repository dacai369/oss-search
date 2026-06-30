# TASK-008 CLI 入口与端到端串联

| 项 | 内容 |
|---|---|
| 编号 | TASK-008 |
| 模块 | cli |
| 优先级 | P0（MVP 收口）|
| 依赖 | TASK-001/002/003/005/006/007 |
| 状态 | ✅ 完成（2026-06-30） |

## 目标
一个命令把整条链路跑通：
```
oss-search "我想做一个文档问答知识库，要自部署" --out report.md
```

## 实现要点
- 串联：parse_intent → 各 enabled 适配器 search → dedup → score → build_report。
- 配置（API key、信源开关、Top-N、权重）走环境变量/配置文件。
- 友好日志：每阶段打印进度与候选数量。

## 验收标准（DoD）
- [x] 单条命令完成端到端，产出 Markdown 报告
- [x] 至少接通 GitHub + npm/PyPI 三个源
- [x] 缺 key / 单源失败时给清晰提示，不整体崩溃
- [x] 引擎可独立运行（README 有说明）
- [x] 用 2 个不同需求各跑出一份合理报告
