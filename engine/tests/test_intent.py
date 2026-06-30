"""TASK-001 验收测试（对应《意图拆解Schema》§4 与字段规则）。

用假 LLM 客户端，不连网。运行：
    cd engine && python -m pytest tests/ -v
    或无 pytest 时：python tests/test_intent.py
"""

import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from oss_search.intent import parse_intent, load_intent_spec
from oss_search.models import IntentSpec


class FakeClient:
    """按预设依次返回响应，记录调用次数。"""
    def __init__(self, responses):
        self.responses = list(responses)
        self.calls = 0

    def chat(self, messages, json_mode=False):
        self.calls += 1
        return self.responses.pop(0)


def cap(cid, name, required=True):
    """构造一个合规能力：中/英各 2 个关键词（满足 validate() 要求）。"""
    return {
        "id": cid,
        "name": name,
        "required": required,
        "keywords_en": [name.lower(), f"{name.lower()}-lib"],
        "keywords_zh": [name, f"{name}组件"],
    }


def _spec_json(summary, caps, constraints=None):
    return json.dumps({
        "summary": summary,
        "constraints": constraints or {},
        "capabilities": caps,
    }, ensure_ascii=False)


def _three_caps():
    """3 个合规能力，required 排序正确（true 在前）。"""
    return [cap("c1", "A", True), cap("c2", "B", True), cap("c3", "C", False)]


# ---- 用例1：中文需求 ----
def test_chinese_request():
    caps = [
        cap("cap-1", "文档解析", True),
        cap("cap-2", "向量检索", True),
        cap("cap-3", "对话编排", False),
    ]
    client = FakeClient([_spec_json("文档问答知识库", caps)])
    spec = parse_intent("做一个内部文档问答知识库", client=client)
    assert isinstance(spec, IntentSpec)
    assert spec.summary == "文档问答知识库"
    assert 3 <= len(spec.capabilities) <= 8
    assert spec.capabilities[0].id == "cap-1"
    assert spec.original_request == "做一个内部文档问答知识库"


# ---- 用例2：英文需求 ----
def test_english_request():
    caps = [cap("c1", "Auth", True), cap("c2", "Rate", True), cap("c3", "Logging", False)]
    client = FakeClient([_spec_json("API gateway", caps)])
    spec = parse_intent("I want to build an API gateway", client=client)
    assert spec.summary == "API gateway"
    assert len(spec.capabilities) == 3


# ---- 用例3：带约束（license + 自托管）----
def test_with_constraints():
    caps = [cap("c1", "切分", True), cap("c2", "检索", True), cap("c3", "存储", True)]
    constraints = {"license_deny": ["GPL-3.0"], "self_host_required": True}
    client = FakeClient([_spec_json("自托管RAG", caps, constraints)])
    spec = parse_intent("要自部署，不要 GPL 的文档问答", client=client)
    assert spec.constraints.self_host_required is True
    assert "GPL-3.0" in spec.constraints.license_deny


# ---- 用例4：模糊需求也能拆 ----
def test_vague_request():
    caps = [cap("c1", "对话", True), cap("c2", "意图识别", True), cap("c3", "多渠道", False)]
    client = FakeClient([_spec_json("聊天机器人", caps)])
    spec = parse_intent("做个聊天机器人", client=client)
    assert len(spec.capabilities) >= 3


# ---- 用例5：首次返回坏 JSON，重试后成功 ----
def test_retry_on_bad_json():
    client = FakeClient(["这不是JSON{坏的", _spec_json("修正后", _three_caps())])
    spec = parse_intent("随便一个需求", client=client)
    assert spec.summary == "修正后"
    assert client.calls == 2  # 确实重试了


# ---- 用例6：能从带前后缀文字的输出里抽 JSON ----
def test_extract_json_from_noisy_output():
    noisy = "好的，结果如下：\n" + _spec_json("带前缀", _three_caps()) + "\n希望有用"
    client = FakeClient([noisy])
    spec = parse_intent("需求", client=client)
    assert spec.summary == "带前缀"


# ---- 用例7：两次都失败则报错 ----
def test_fail_after_retries():
    client = FakeClient(["坏的", "还是坏的"])
    try:
        parse_intent("需求", client=client)
        assert False, "应当抛出 ValueError"
    except ValueError:
        pass


# ---- 用例8：空需求直接报错 ----
def test_empty_request():
    try:
        parse_intent("   ", client=FakeClient(["{}"]))
        assert False, "应当抛出 ValueError"
    except ValueError:
        pass


# ---- 用例9：主路径 load_intent_spec（skill 模式，agent 已出 JSON）----
def test_load_intent_spec_valid():
    data = {"summary": "宿主agent的产物", "constraints": {}, "capabilities": _three_caps()}
    spec = load_intent_spec(data, original_request="某需求")
    assert isinstance(spec, IntentSpec)
    assert spec.summary == "宿主agent的产物"
    assert spec.original_request == "某需求"


# ---- 用例10：主路径校验非法输入（空能力）----
def test_load_intent_spec_invalid():
    try:
        load_intent_spec({"summary": "缺能力", "capabilities": []})
        assert False, "应当抛出 ValueError"
    except ValueError:
        pass


# ---- 用例11：能力数量越界（<3）应报错 ----
def test_too_few_capabilities():
    data = {"summary": "只有2个能力", "capabilities": [cap("c1", "A"), cap("c2", "B")]}
    try:
        load_intent_spec(data)
        assert False, "应当抛出 ValueError（能力数量 < 3）"
    except ValueError as e:
        assert "3-8" in str(e)


# ---- 用例12：能力数量越界（>8）应报错 ----
def test_too_many_capabilities():
    caps = [cap(f"c{i}", f"N{i}") for i in range(9)]
    try:
        load_intent_spec({"summary": "9个能力", "capabilities": caps})
        assert False, "应当抛出 ValueError（能力数量 > 8）"
    except ValueError:
        pass


# ---- 用例13：关键词不足 2 个应报错 ----
def test_insufficient_keywords():
    bad = {"id": "c1", "name": "X", "required": True,
           "keywords_en": ["only-one"], "keywords_zh": ["仅一个"]}
    data = {"summary": "关键词不够", "capabilities": [bad, cap("c2", "B"), cap("c3", "C")]}
    try:
        load_intent_spec(data)
        assert False, "应当抛出 ValueError（关键词 < 2）"
    except ValueError as e:
        assert "keywords" in str(e)


# ---- 用例14：required 排序错误（必需在可选之后）应报错 ----
def test_bad_required_ordering():
    caps = [cap("c1", "A", required=False),
            cap("c2", "B", required=True),
            cap("c3", "C", required=True)]
    try:
        load_intent_spec({"summary": "排序错", "capabilities": caps})
        assert False, "应当抛出 ValueError（required:true 须在前）"
    except ValueError as e:
        assert "排序" in str(e)


def _run_all():
    """无 pytest 时的简易跑测。"""
    fns = [v for k, v in sorted(globals().items()) if k.startswith("test_") and callable(v)]
    passed = 0
    for fn in fns:
        fn()
        print(f"  ✓ {fn.__name__}")
        passed += 1
    print(f"\n全部通过：{passed}/{len(fns)}")


if __name__ == "__main__":
    _run_all()
