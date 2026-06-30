# 引擎（oss_search）

Python 3.11+，可脱离 Skill / AI 工具单独运行。

## 安装

```bash
pip install -e .
oss-search  # 打印帮助即成功
```

## LLM 配置

**Skill 模式（推荐）**：不需要任何 key，意图拆解由宿主 agent 完成。

**单独运行（可选）**：引擎自带兜底 LLM，支持任意 OpenAI 兼容端点：
```bash
export LLM_API_KEY=sk-xxx
export LLM_BASE_URL=https://api.deepseek.com  # 或其他兼容服务
export LLM_MODEL=deepseek-chat
pip install openai
```

## 跑测试

```bash
python3 -m pytest tests/ -v
```

## 模块说明

```
oss_search/
  models.py       # 数据结构：IntentSpec / Capability / Candidate / ScoredCandidate
  intent.py       # 意图拆解：load_intent_spec()（主）/ parse_intent()（兜底）
  collect.py      # GitHub 采集适配器
  adapters.py     # npm + PyPI 采集适配器
  merge.py        # 归并去重
  score.py        # 质量评级（6 维加权）
  report.py       # 报告生成（Markdown + 自包含 HTML）
  llm_client.py   # 可选 LLM 客户端（兜底模式用）
  config.py       # 信源清单加载
  __main__.py     # CLI 入口
```
