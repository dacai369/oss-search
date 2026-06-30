# 开源意图搜索器 (OSS Intent Search)

> 输入你想做的功能/架构，自动拆解成能力清单，跨 GitHub + npm + PyPI 多源搜索，质量评级，给出选型建议。

## 一句话定位

**意图驱动的开源选型助手**——不是让你想关键词，而是从需求倒推该用什么。

## 快速安装

### 方式 1：pip 安装（推荐，装后全局可用 `oss-search` 命令）

```bash
git clone <repo-url> && cd <repo>
pip install -e ./engine
oss-search  # 验证：应打印帮助
```

### 方式 2：作为 AI Skill 安装（Claude Code / Cursor / Hermes）

本仓库根目录下的 `SKILL.md` 即 Skill 文件，复制到你的 AI 工具 skills 目录即可。

- **Claude Code**: `cp SKILL.md ~/.claude/skills/oss-search.md`
- **Cursor**: 复制到 `.cursor/skills/` 或项目根目录
- **Hermes**: `cp SKILL.md ~/.hermes/skills/`

### 方式 3：无需安装直接跑（零配置）

```bash
cd engine
python3 -m oss_search search --json <intent_spec.json> --out report --md --html
```

引擎纯 stdlib，零外部依赖。

---

## 首次配置

**LLM 不需要 key**——意图拆解由宿主 agent（Claude / Cursor / Hermes）完成。

仅建议配 `GITHUB_TOKEN`（GitHub 限流优化，60→5000 req/h），缺了也能跑：

```bash
export GITHUB_TOKEN=ghp_xxx  # 可选
```

脱离 agent 单独跑时如需兜底 LLM（可选）：
```bash
pip install openai  # 仅兜底模式需要
export LLM_API_KEY=sk-xxx  # 任意 OpenAI 兼容端点
```

---

## 使用示例

### 通过 Skill（一句话触发）
```
用户: 帮我找个自部署的文档问答知识库，要支持中文
→ agent 拆解 IntentSpec → oss-search search --json ... → 返回报告
```

### 通过命令行（已有 IntentSpec JSON）
```bash
oss-search search \
  --json intent_spec.json \
  --out report \
  --md --html --top-n 5
```

输出：`report.md`（可读）+ `report.html`（浏览器直接打开）。

### 追加自定义信源
```bash
oss-search search \
  --json intent_spec.json \
  --out report --md --html \
  --source https://example.com/opensource-projects \
  --source https://another-site.com/feed.xml
```

> ⚠️ MVP 阶段自定义源只做登记展示（报告标「已记录·采集待 V2」），真抓留给后续版本。

---

## 运行测试

```bash
cd engine
python3 tests/test_intent.py      # 意图拆解 (14 tests)
python3 tests/test_collect.py     # GitHub 适配器 (9 tests)
python3 tests/test_adapters.py    # npm + PyPI (9 tests)
python3 tests/test_merge.py       # 归并去重 (16 tests)
python3 tests/test_score.py       # 评分引擎 (28 tests)
python3 tests/test_report.py      # 报告生成 (10 tests)
python3 tests/test_cli.py         # CLI 端到端 (9 tests)
```

全部通过：**95/95**。

---

## 目录结构

```
开源意图搜索器/
├── SKILL.md              # AI Skill（入口文件）
├── README.md             # 本文件
├── 进度看板.md            # 任务状态总表
├── 规范/                  # 技术规范 + Schema + 信源清单
├── 任务卡/                # TASK-001 ~ TASK-010
└── engine/               # Python 引擎
    ├── pyproject.toml     # pip 安装配置
    ├── oss_search/        # 核心引擎模块
    │   ├── intent.py      # 意图拆解 + 校验
    │   ├── collect.py     # GitHub 适配器
    │   ├── adapters.py    # npm + PyPI
    │   ├── merge.py       # 归并去重
    │   ├── score.py       # 质量评级
    │   ├── report.py      # 报告生成 (MD + HTML)
    │   └── __main__.py    # CLI 入口
    └── tests/             # 95 个测试
```

## MVP 范围

需求 → 意图拆解 → GitHub + npm + PyPI → 归并去重 → 质量评级 → 选型报告（MD + HTML）

中文内容源（公众号/掘金）为 V2 增量。

## 技术决策

| 事项 | 决策 |
|------|------|
| LLM | 由宿主 agent 提供，引擎不绑 provider（ADR-005） |
| Embedding | MVP 用 BM25 降级（ADR-006） |
| 接口 | Skill 封装 + 静态 HTML 报告（ADR-007） |
| 信源 | 内置白名单 + 运行时自定义源（ADR-008） |
| 分发 | GitHub skill + pip 安装（ADR-009） |

---

## License

MIT
