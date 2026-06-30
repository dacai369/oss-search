"""LLM 客户端：**可选**（对应修订后的 ADR-005）。

主路径下引擎不需要它——意图拆解等"动脑"步骤由宿主 agent（Claude Code / Cursor / …）完成，
agent 直接产出 IntentSpec JSON，引擎用 load_intent_spec() 校验加载。

本模块只用于「脱离 agent 单独跑 / CI」的兜底场景：用任意 OpenAI 兼容端点。
不绑定 DeepSeek——provider 通过环境变量配置，DeepSeek 只是默认示例。
openai 依赖在方法内惰性导入，不装也能 import 本模块。
"""

from __future__ import annotations

import os
from typing import Dict, List, Protocol


class LLMClient(Protocol):
    """最小接口。测试可注入假实现；skill 模式下根本用不到。"""
    def chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        ...


class OpenAICompatibleClient:
    """可选兜底：任意 OpenAI 兼容端点。

    配置优先级：构造参数 > 环境变量。环境变量：
      LLM_API_KEY（兼容 DEEPSEEK_API_KEY）、LLM_BASE_URL、LLM_MODEL
    默认指向 DeepSeek，仅作示例，可换成任何兼容服务。
    """

    def __init__(self, api_key: str = "", model: str = "", base_url: str = "", timeout: float = 60.0):
        self.api_key = (
            api_key
            or os.environ.get("LLM_API_KEY")
            or os.environ.get("DEEPSEEK_API_KEY", "")
        )
        self.base_url = base_url or os.environ.get("LLM_BASE_URL", "https://api.deepseek.com")
        self.model = model or os.environ.get("LLM_MODEL", "deepseek-chat")
        self.timeout = timeout
        if not self.api_key:
            raise ValueError(
                "缺少 LLM API key（LLM_API_KEY / DEEPSEEK_API_KEY）。"
                "注意：skill 模式下无需 key——LLM 由宿主 agent 提供。"
            )

    def chat(self, messages: List[Dict[str, str]], json_mode: bool = False) -> str:
        try:
            from openai import OpenAI
        except ImportError as e:
            raise ImportError("需要 openai 库：pip install openai（兜底模式才需要）") from e

        client = OpenAI(api_key=self.api_key, base_url=self.base_url, timeout=self.timeout)
        kwargs = {"model": self.model, "messages": messages, "temperature": 0.2}
        if json_mode:
            kwargs["response_format"] = {"type": "json_object"}
        resp = client.chat.completions.create(**kwargs)
        return resp.choices[0].message.content or ""
