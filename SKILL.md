---
name: oss-search
description: >
  开源选型 / 技术调研 / "有没有现成的轮子"。把需求拆成能力清单，跨 GitHub + npm + PyPI
  多源搜索，合并去重后给出评分评级与组合方案建议，输出 Markdown + 自包含 HTML 报告。
  支持运行时追加自定义信源 URL。
---

# 开源意图搜索器 (oss-search)

一句话：**把你脑子里"我想找个开源方案"变成一份评分排序的报告。**

你不需要知道搜什么关键词、怎么评估好坏、怎么跨源去重——描述你的需求和约束，
引擎帮你拆解、搜索、打分、生成报告。

## 触发场景

当用户说以下任何一类话时，加载此 skill：

- 「帮我找个...的开源方案」「有没有现成的轮子」
- 「技术选型：...」「对比一下市面上的...」
- 「我想做一个...，需要自部署/开源」
- 任何带有明确技术需求 + "开源/免费/自托管"语义的请求

## 工作流程

### 第 1 步：意图拆解（你来做）

把用户需求拆成 `IntentSpec` JSON。这是引擎的"菜单"——告诉它搜什么、有哪些约束。

**Schema**（严格遵循，不要输出任何解释文字，只输出 JSON）：

```json
{
  "original_request": "用户原文",
  "summary": "一句话概括",
  "constraints": {
    "languages": [],
    "license_allow": [],
    "license_deny": [],
    "self_host_required": false,
    "deployment": ""
  },
  "capabilities": [
    {
      "id": "cap-1",
      "name": "能力名称",
      "description": "这个能力做什么",
      "required": true,
      "keywords_en": ["keyword1", "keyword2"],
      "keywords_zh": ["关键词1", "关键词2"],
      "candidate_topics": ["GitHub-topic1", "GitHub-topic2"],
      "candidate_packages": ["npm或pypi包名1"]
    }
  ]
}
```

**拆解规则**：
- 拆成 3-8 个原子能力，`required:true` 的放前面
- 每个能力中英文关键词各 ≥2 个（引擎强校验）
- candidate_topics 填 GitHub topic，候选包名填 npm/PyPI 包名，不确定就空数组
- 约束（语言/许可证/部署）**只填用户明确提到的**，没提的留空，不臆造
- `summary` 用中文总结，`keywords_en` 贴近开源世界术语（不用口语）

把 JSON 写入临时文件，例如 `/tmp/intent_spec.json`。

### 第 2 步：跑引擎

```bash
cd /Users/dacai/Documents/github笔记/开源意图搜索器/engine

python3 -m oss_search search \
  --json /tmp/intent_spec.json \
  --out /tmp/oss_report \
  --md --html --top-n 5
```

如果用户给了自定义信源 URL（"也扫一下这个站：URL"），追加 `--source`：

```bash
python3 -m oss_search search \
  --json /tmp/intent_spec.json \
  --out /tmp/oss_report \
  --md --html --top-n 5 \
  --source https://用户给的URL
```

### 第 3 步：返回结果

引擎输出文件路径是 `/tmp/oss_report.md` 和 `/tmp/oss_report.html`。

告诉用户：
- Markdown 报告路径（可直接读、编辑）
- HTML 报告路径（可直接浏览器打开）
- 简要摘要：几个候选、什么评级分布、首选推荐

## 对宿主 agent 的要求

- **由你（宿主 agent）做意图拆解**，无需额外 LLM key
- **GITHUB_TOKEN 建议配置**（仅 GitHub 限流用，5000 req/h vs 60 req/h），不是必须——缺 token 引擎照跑但 GitHub 可能慢
- 引擎完全离线可测试：`python3 -m oss_search` 无线索也能打印帮助

## 向用户展示的报告样例

引擎产出的 Markdown 报告包含：
- 📋 需求回显
- 📡 本次使用信源列表（含运行时自定义源）
- 📊 候选评估表（按能力分组，评分/评级/⭐/License/理由）
- 💡 整体组合建议
- ⚠️ 风险提示

## 环境依赖

```bash
# 引擎本身零外部依赖（仅 stdlib）
cd engine && python3 -m oss_search  # 打印帮助即成功
```

如果需要兜底 LLM（脱离 agent 单独跑），可选安装：
```bash
pip install openai  # 仅兜底 LLM 模式需要，skill 模式不需要
```

## 注意事项

- 此 skill **不绑定任何 LLM provider**，不要求任何 API key（ADR-005）
- GITHUB_TOKEN 仅为 GitHub 限流优化，缺了也能跑
- 报告中的评分和理由是引擎基于 BM25 + 多维规则的确定性计算，不是 LLM 生成的
- 自定义信源格式见 ADR-008：通过 `--source URL` 传入，报告中会展示
