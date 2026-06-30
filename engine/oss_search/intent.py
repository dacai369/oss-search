"""意图拆解模块。

两条路径：
- 主路径 load_intent_spec(data)：宿主 agent 已产出 JSON，引擎只校验加载（Skill 模式）。
- 兜底 parse_intent(request)：脱离 agent 单跑时，用可选 LLM 客户端自己拆。
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Optional

from .llm_client import LLMClient, OpenAICompatibleClient
from .models import IntentSpec


SCHEMA_HINT = """{
  "summary": "一句话概括要做什么",
  "constraints": {
    "languages": [], "license_allow": [], "license_deny": [],
    "self_host_required": false, "deployment": ""
  },
  "capabilities": [
    {
      "id": "cap-1", "name": "能力名", "description": "做什么",
      "required": true,
      "keywords_en": ["term"], "keywords_zh": ["术语"],
      "candidate_topics": ["topic"], "candidate_packages": ["pkg"]
    }
  ]
}"""

SYSTEM_PROMPT = (
    "你是开源选型的需求分析专家。把用户的功能/架构需求拆解成「能力清单」。\n"
    "要求：\n"
    "1. 只输出一个合法 JSON，结构严格遵循给定 Schema，不要任何解释文字。\n"
    "2. 把需求拆成 3-8 个原子能力，每个能力是一个可以独立去找开源方案的功能点。\n"
    "3. 能力按重要性排序，必需的(required:true)在前。\n"
    "4. 每个能力给中英文关键词、可能的 GitHub topic、可能的包名（拿不准就留空数组）。\n"
    "5. 约束(语言/许可证/部署)只填用户明确提到的，没提的留空。\n"
    "6. 关键词用领域术语，不用口语。\n\n"
    "Schema:\n" + SCHEMA_HINT
)


def _extract_json(text: str) -> dict:
    """从模型输出里抽出 JSON 对象。优先整体解析，失败则截取首个 {...}。"""
    text = text.strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    m = re.search(r"\{.*\}", text, re.DOTALL)
    if m:
        return json.loads(m.group(0))
    raise ValueError("模型未返回可解析的 JSON")


def load_intent_spec(data: Dict[str, Any], original_request: str = "") -> IntentSpec:
    """主路径（skill 模式）：宿主 agent 已产出 JSON，引擎校验并加载。

    Args:
        data: 符合《意图拆解Schema》的 dict（agent 输出，已是对象）。
        original_request: 用户原始需求，便于回显。

    Raises:
        ValueError: data 不符合 schema。
    """
    spec = IntentSpec.from_dict(data, original_request=original_request)
    errs = spec.validate()
    if errs:
        raise ValueError("IntentSpec 校验失败：" + "；".join(errs))
    return spec


def parse_intent(request: str, client: Optional[LLMClient] = None) -> IntentSpec:
    """兜底路径（脱离 agent 单跑）：用可选 LLM 客户端自己拆。

    Args:
        request: 用户需求（中/英）。
        client: LLM 客户端，便于测试注入。默认用通用 OpenAI 兼容客户端。

    Raises:
        ValueError: 重试后仍无法得到合法 IntentSpec。
    """
    if not request or not request.strip():
        raise ValueError("需求不能为空")

    client = client or OpenAICompatibleClient()
    messages = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": "用户需求：\n" + request.strip()},
    ]

    last_err = ""
    for attempt in range(2):  # 失败重试 1 次（共 2 次）
        raw = client.chat(messages, json_mode=True)
        try:
            data = _extract_json(raw)
            return load_intent_spec(data, original_request=request.strip())
        except (ValueError, json.JSONDecodeError) as e:
            last_err = str(e)
        # 把错误反馈给模型，促其修正
        messages.append({"role": "assistant", "content": raw})
        messages.append(
            {"role": "user", "content": f"上次输出有问题：{last_err}。请只输出修正后的合法 JSON。"}
        )

    raise ValueError(f"意图拆解失败：{last_err}")
