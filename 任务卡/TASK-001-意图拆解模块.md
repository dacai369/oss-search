# TASK-001 意图拆解模块

| 项 | 内容 |
|---|---|
| 编号 | TASK-001 |
| 模块 | intent |
| 优先级 | P0（地基） |
| 依赖 | 无 |
| 状态 | ✅ 完成（2026-06-30，指挥官验收通过） |

## 目标
实现 `parse_intent(request: str) -> IntentSpec`，把自然语言需求拆成结构化能力清单。

## 输入 / 输出
- 输入：用户需求字符串（中/英）
- 输出：符合 [意图拆解Schema.md](../规范/意图拆解Schema.md) 的 IntentSpec（dataclass + 合法 JSON）

## 实现要点
- 用 Claude + 规范里的系统提示词；强制 JSON 输出。
- 做一次 JSON 解析校验 + 必填字段校验，失败重试 1 次。
- 不引入 Agent（ADR-001）。接口签名固定，便于未来替换。

## 验收标准（DoD）
- [x] 接口签名与 [技术规范.md §5](../规范/技术规范.md) 一致
- [x] 通过 Schema 文档 §4 的 4 个验收用例
- [x] 中文/英文需求都能拆出 3-8 个能力
- [x] 输出可被 `json.loads` 解析，必填字段齐全
- [x] 有最小单元测试覆盖上述用例

## 交付物
- `engine/oss_search/models.py`（IntentSpec/Capability/Constraints + Candidate 占位）
- `engine/oss_search/llm_client.py`（**可选**通用 OpenAI 兼容客户端，不绑 provider）
- `engine/oss_search/intent.py`：
  - `load_intent_spec(data)` —— **主路径**：宿主 agent 出 JSON，引擎校验加载（skill 模式）
  - `parse_intent(request)` —— 兜底：脱离 agent 单跑时自己拆
- `engine/tests/test_intent.py`（10 用例，`python3 tests/test_intent.py` 全过）

## 备注（ADR-005 修订后）
- skill 模式下意图拆解由**宿主 agent**完成，**不需要任何 key**。SYSTEM_PROMPT 复用为写进 SKILL.md 的指令模板。
- 单测全程不连网。兜底客户端走 `LLM_BASE_URL/LLM_API_KEY/LLM_MODEL`，仅可选。
