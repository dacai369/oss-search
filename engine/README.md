# 引擎（oss_search）

核心引擎，可脱离 Skill / Claude 单独运行（ADR-007）。Python 3.11+。

## LLM 说明（ADR-005 修订）
意图拆解等"动脑"步骤**由宿主 agent 完成**（Claude Code/Cursor/…），引擎不绑 provider、不要 key。
脱离 agent 单跑时才需要可选的兜底客户端：
```bash
export LLM_API_KEY=sk-xxx                 # 任意 OpenAI 兼容端点
export LLM_BASE_URL=https://api.deepseek.com   # 默认示例，可换
export LLM_MODEL=deepseek-chat
```

## 安装
```bash
cd engine
pip install -r requirements.txt          # 仅兜底 LLM 客户端需要 openai
```

## 跑测试（不连网，用假客户端）
```bash
python3 tests/test_intent.py             # 无 pytest 也能跑
# 或： python -m pytest tests/ -v
```

## 已实现
- **TASK-001 意图拆解**：
  - 主路径 `load_intent_spec(data)`：宿主 agent 出 JSON，引擎校验加载（skill 模式）
  - 兜底 `parse_intent(request)`：脱离 agent 单跑时自己拆

```python
from oss_search.intent import load_intent_spec
# data 来自宿主 agent 按《意图拆解Schema》产出的 JSON
spec = load_intent_spec(data, original_request="做一个文档问答知识库")
print(spec.summary, [c.name for c in spec.capabilities])
```

## 目录
```
oss_search/
  models.py       # IntentSpec / Capability / Constraints / Candidate
  llm_client.py   # 通用 OpenAI 兼容客户端（可选兜底，openai 惰性导入，不绑 provider）
  intent.py       # load_intent_spec（主）/ parse_intent（兜底）（TASK-001）
  __main__.py     # CLI 入口：python -m oss_search（最小骨架，收口于 TASK-008）
tests/
  test_intent.py
pyproject.toml    # 打包/依赖声明（requires-python>=3.11）
```
