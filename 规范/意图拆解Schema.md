# 意图拆解 Schema 与 Prompt

## 1. 输出 JSON Schema（IntentSpec）

```json
{
  "original_request": "用户原始需求原文",
  "summary": "一句话概括要做什么",
  "constraints": {
    "languages": ["Python"],
    "license_allow": ["MIT", "Apache-2.0"],
    "license_deny": ["GPL-3.0"],
    "self_host_required": false,
    "deployment": "云/边缘/本地，无则空串"
  },
  "capabilities": [
    {
      "id": "cap-1",
      "name": "全文检索",
      "description": "对文档做关键词+语义检索",
      "required": true,
      "keywords_en": ["full-text search", "vector search"],
      "keywords_zh": ["全文检索", "向量检索"],
      "candidate_topics": ["search", "elasticsearch", "vector-database"],
      "candidate_packages": ["meilisearch", "typesense", "qdrant"]
    }
  ]
}
```

### 字段规则
- `capabilities` 为 3-8 项，按重要性排序，`required:true` 在前（引擎校验数量与排序）。
- `keywords_en` / `keywords_zh` 各至少 2 个，供查询扩展层使用（引擎强校验）。
- `candidate_topics` 对应 GitHub topic；`candidate_packages` 对应 npm/PyPI 包名（不确定可留空数组）。
- 不臆造约束：用户没提的 license / 语言就留空，不要瞎填。

## 2. Prompt（系统提示词）

```
你是开源选型的需求分析专家。把用户的功能/架构需求拆解成「能力清单」。

要求：
1. 只输出一个合法 JSON，结构严格遵循给定 Schema，不要任何解释文字。
2. 把需求拆成 3-8 个原子能力，每个能力是一个可以独立去找开源方案的功能点。
3. 能力按重要性排序，必需的(required:true)在前。
4. 每个能力给出中英文关键词、可能的 GitHub topic、可能的包名（拿不准就留空数组）。
5. 约束(语言/许可证/部署)只填用户明确提到的，没提的留空。
6. 关键词要贴近开源世界的真实叫法（用领域术语，不用口语）。

Schema:
<这里贴上第1节的 Schema>

用户需求：
<request>
```

## 3. 示例（输入→输出）

**输入**：「我想做一个能把内部文档变成可对话知识库的系统，要能自部署，不要 GPL」

**输出**（节选）：
```json
{
  "summary": "自托管的文档问答(RAG)知识库系统",
  "constraints": {
    "languages": [],
    "license_allow": [],
    "license_deny": ["GPL-3.0", "AGPL-3.0"],
    "self_host_required": true,
    "deployment": "本地/私有部署"
  },
  "capabilities": [
    {
      "id": "cap-1", "name": "文档解析与切分", "required": true,
      "keywords_en": ["document loader", "text splitter", "chunking"],
      "keywords_zh": ["文档解析", "文本切分"],
      "candidate_topics": ["document-parsing", "rag"],
      "candidate_packages": ["unstructured", "llama-index"]
    },
    {
      "id": "cap-2", "name": "向量检索", "required": true,
      "keywords_en": ["vector database", "semantic search"],
      "keywords_zh": ["向量数据库", "语义检索"],
      "candidate_topics": ["vector-database", "embeddings"],
      "candidate_packages": ["qdrant", "chroma", "milvus"]
    }
  ]
}
```

## 4. 测试用例参考
覆盖场景：中文需求、英文需求、带约束（license/自托管）、不带约束、模糊需求（如「做个聊天机器人」）。
