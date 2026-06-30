# 开源选型报告：自托管文档问答知识库

## 📋 需求
> **原始需求**：做一个文档问答知识库，要自部署，不要GPL
> **概括**：自托管文档问答知识库
> **排除许可证**：GPL-3.0
> **必须自托管**

## 📊 候选评估
### ▸ 全文检索 (`cap-1`)
**候选数**：15 | **展示 Top-5**

| # | 项目 | 评分 | 评级 | ⭐ | License | 理由 |
|---|------|------|------|----|---------|------|
| 1 | [oramasearch/orama](https://github.com/oramasearch/orama) | 0.6101 | **C** | 10,456 | NOASSERTION | 契合度低：项目描述与需求关联弱 |
| 2 | [infiniflow/infinity](https://github.com/infiniflow/infinity) | 0.5943 | **C** | 4,590 | Apache-2.0 | 契合度低：项目描述与需求关联弱 |
| 3 | [oceanbase/pyobvector](https://github.com/oceanbase/pyobvector) | 0.5202 | **C** | 19 | Apache-2.0 | 契合度低：项目描述与需求关联弱 |
| 4 | [cyberlife-coder/VelesDB](https://github.com/cyberlife-coder/VelesDB) | 0.5196 | **C** | 72 | NOASSERTION | 契合度低：项目描述与需求关联弱 |
| 5 | [infino-ai/infino](https://github.com/infino-ai/infino) | 0.4865 | **D** | 11 | Apache-2.0 | 契合度低：项目描述与需求关联弱 |

### 1. [oramasearch/orama](https://github.com/oramasearch/orama)
>🌌  A complete search engine and RAG pipeline in your browser, server or edge network with support for full-text, vector, and hybrid search in less than 2kb.
- **综合评分**：`0.6101` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（2天内有提交）
  - 社区活跃（10,456 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（15个），有README
  - 许可证 NOASSERTION，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/oramasearch/orama](https://github.com/oramasearch/orama)

### 2. [infiniflow/infinity](https://github.com/infiniflow/infinity)
>The AI-native database built for LLM applications, providing incredibly fast hybrid search of dense vector, sparse vector, tensor (multi-vector), and full-text.
- **综合评分**：`0.5943` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（0天内有提交）
  - 有一定社区基础（4,590 ⭐，430 fork）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（19个），有README
  - 许可证 Apache-2.0，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/infiniflow/infinity](https://github.com/infiniflow/infinity)

### 3. [oceanbase/pyobvector](https://github.com/oceanbase/pyobvector)
>A Python SDK for OceanBase Multimodal Store—enabling vector search, full-text search, and JSON table operations—offers both Milvus-compatible API and SQLAlchemy-based SQL mode, and supports both Ocean
- **综合评分**：`0.5202` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（24天内有提交）
  - 社区较小（19 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（5个），有README
  - 许可证 Apache-2.0，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/oceanbase/pyobvector](https://github.com/oceanbase/pyobvector)

### 4. [cyberlife-coder/VelesDB](https://github.com/cyberlife-coder/VelesDB)
>VelesDB is a local‑first AI data engine written in Rust that unifies vectors, full‑text and graph in a single file with a familiar SQL‑like language.  Instead of sending every RAG or semantic search q
- **综合评分**：`0.5196` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（0天内有提交）
  - 社区较小（72 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（18个），有README
  - 许可证 NOASSERTION，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/cyberlife-coder/VelesDB](https://github.com/cyberlife-coder/VelesDB)

### 5. [infino-ai/infino](https://github.com/infino-ai/infino)
>Fast search engine on object storage, with full text search, vectors, and SQL, natively on Parquet.
- **综合评分**：`0.4865` / **D**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（0天内有提交）
  - 社区较小（11 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（12个），有README
  - 许可证 Apache-2.0，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/infino-ai/infino](https://github.com/infino-ai/infino)

### ▸ 文档解析 (`cap-2`)
**候选数**：15 | **展示 Top-5**

| # | 项目 | 评分 | 评级 | ⭐ | License | 理由 |
|---|------|------|------|----|---------|------|
| 1 | [RediSearch/RediSearch](https://github.com/RediSearch/RediSearch) | 0.5882 | **C** | 6,163 | NOASSERTION | 契合度低：项目描述与需求关联弱 |
| 2 | [gordonmurray/firnflow](https://github.com/gordonmurray/firnflow) | 0.5326 | **C** | 414 | Apache-2.0 | 契合度低：项目描述与需求关联弱 |
| 3 | [langchain-ai/langchain-milvus](https://github.com/langchain-ai/langchain-milvus) | 0.511 | **C** | 56 | MIT | 契合度低：项目描述与需求关联弱 |
| 4 | [neurondb/neurondb](https://github.com/neurondb/neurondb) | 0.4753 | **D** | 50 | NOASSERTION | 契合度低：项目描述与需求关联弱 |
| 5 | [kuzudb/kuzu](https://github.com/kuzudb/kuzu) | 0.4736 | **D** | 3,992 | MIT | 契合度低：项目描述与需求关联弱 |

### 1. [RediSearch/RediSearch](https://github.com/RediSearch/RediSearch)
>A query and indexing engine for Redis, providing secondary indexing, full-text search, vector similarity search and aggregations.
- **综合评分**：`0.5882` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（0天内有提交）
  - 有一定社区基础（6,163 ⭐，585 fork）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（9个），有README
  - 许可证 NOASSERTION，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/RediSearch/RediSearch](https://github.com/RediSearch/RediSearch)

### 2. [gordonmurray/firnflow](https://github.com/gordonmurray/firnflow)
>The cost efficiency of S3 with the speed of local RAM. A multi-tenant vector and full-text search engine featuring a tiered RAM -> NVMe -> S3 architecture for microsecond latency on   top of object st
- **综合评分**：`0.5326` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（6天内有提交）
  - 社区规模中等（414 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，有README
  - 许可证 Apache-2.0，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/gordonmurray/firnflow](https://github.com/gordonmurray/firnflow)

### 3. [langchain-ai/langchain-milvus](https://github.com/langchain-ai/langchain-milvus)
>The LangChain wrapper of Milvus vector database for efficient vector search, full-text search, hybrid retrieval and RAG.
- **综合评分**：`0.511` / **C**
  - 契合度低：项目描述与需求关联弱
  - 近期活跃（22天内有提交）
  - 社区较小（56 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，有README
  - 许可证 MIT，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/langchain-ai/langchain-milvus](https://github.com/langchain-ai/langchain-milvus)

### 4. [neurondb/neurondb](https://github.com/neurondb/neurondb)
>NeuronDB PostgreSQL extension: vector similarity search (HNSW, IVFFlat), embeddings, kNN, ML in SQL, and hybrid full-text + vector retrieval.
- **综合评分**：`0.4753` / **D**
  - 契合度低：项目描述与需求关联弱
  - 近56天内有提交，维护正常
  - 社区较小（50 ⭐）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（18个），有README
  - 许可证 NOASSERTION，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/neurondb/neurondb](https://github.com/neurondb/neurondb)

### 5. [kuzudb/kuzu](https://github.com/kuzudb/kuzu)
>Embedded property graph database built for speed. Vector search and full-text search built in. Implements Cypher.
- **综合评分**：`0.4736` / **D**
  - 契合度低：项目描述与需求关联弱
  - 距今262天，可能维护放缓
  - 有一定社区基础（3,992 ⭐，498 fork）
  - 项目成熟度较好：有明确许可证，描述详细，标签齐全（11个），有README
  - 许可证 MIT，无约束冲突
  - 安全评估待接入（MVP 无 CVE 扫描）
- **链接**：[https://github.com/kuzudb/kuzu](https://github.com/kuzudb/kuzu)

## 💡 整体组合建议
**首选推荐**：[oramasearch/orama](https://github.com/oramasearch/orama)（C 级，0.6101 分）

无 A 级项目，0 个 B 级可选。建议放宽搜索条件或关注新兴项目。

## ⚠️ 风险提示
- infino-ai/infino: 综合评级为 D，建议谨慎使用
- neurondb/neurondb: 综合评级为 D，建议谨慎使用
- kuzudb/kuzu: 综合评级为 D，建议谨慎使用
- jeffhajewski/latticedb: 综合评级为 D，建议谨慎使用
- jeffhajewski/latticedb: 社区极小（9 ⭐），可能缺乏长期维护
- trvon/yams: 综合评级为 D，建议谨慎使用
- trvon/yams: 使用 GPL-3.0 许可证，注意合规风险
- L-Defraiteur/lucivy: 综合评级为 D，建议谨慎使用
- prrao87/lancedb-study: 综合评级为 D，建议谨慎使用
- predictable-labs/ryugraph: 综合评级为 D，建议谨慎使用
- zilliztech/milvus-skill: 综合评级为 D，建议谨慎使用
- myscale/MyScaleDB: 综合评级为 D，建议谨慎使用
- myscale/MyScaleDB: 活跃度低，项目可能已停滞
- oramasearch/oramacore: 综合评级为 D，建议谨慎使用
- oramasearch/oramacore: 使用 AGPL-3.0 许可证，注意合规风险
- mhowerton91/history: 综合评级为 D，建议谨慎使用
- mhowerton91/history: 未声明许可证，存在法律风险
- mhowerton91/history: 活跃度低，项目可能已停滞
- arashstar1/bot-lua: 综合评级为 D，建议谨慎使用
- arashstar1/bot-lua: 未声明许可证，存在法律风险
- arashstar1/bot-lua: 活跃度低，项目可能已停滞
- CocaineCong/tangseng: 综合评级为 D，建议谨慎使用
- CocaineCong/tangseng: 活跃度低，项目可能已停滞
- zszszszsz/.config: 综合评级为 D，建议谨慎使用
- zszszszsz/.config: 活跃度低，项目可能已停滞
- damoti/django-tsvector-field: 综合评级为 D，建议谨慎使用
- damoti/django-tsvector-field: 活跃度低，项目可能已停滞
- zepdb/zeppelin: 综合评级为 D，建议谨慎使用
- zepdb/zeppelin: 未声明许可证，存在法律风险
- abdelhai/oakdb: 综合评级为 D，建议谨慎使用
- abdelhai/oakdb: 活跃度低，项目可能已停滞
- SaidiSouhaieb/promptly-lite: 综合评级为 D，建议谨慎使用
- SaidiSouhaieb/promptly-lite: 活跃度低，项目可能已停滞
- farouqzaib/mettis: 综合评级为 D，建议谨慎使用
- farouqzaib/mettis: 未声明许可证，存在法律风险
- farouqzaib/mettis: 活跃度低，项目可能已停滞
- NhaPhatHanh/github: 综合评级为 D，建议谨慎使用
- NhaPhatHanh/github: 未声明许可证，存在法律风险
- NhaPhatHanh/github: 活跃度低，项目可能已停滞
- chikitang/A: 综合评级为 D，建议谨慎使用
- chikitang/A: 未声明许可证，存在法律风险
- chikitang/A: 活跃度低，项目可能已停滞
- mohamedScikitLearn/Information-retrieval--Text-mining-: 综合评级为 D，建议谨慎使用
- mohamedScikitLearn/Information-retrieval--Text-mining-: 未声明许可证，存在法律风险
- mohamedScikitLearn/Information-retrieval--Text-mining-: 活跃度低，项目可能已停滞

---
*报告由 开源意图搜索器 (oss-search) 生成 · 30 个候选评估*