# Hierarchical Chunk Strategy

该目录实现以下入库链路：文档分析、文档树、分层切块、上下文增强、metadata、父子映射、Embedding、Milvus。

默认复用项目已有配置：

- Embedding：SiliconFlow `Pro/BAAI/bge-m3`
- Milvus：`http://localhost:19530`
- Database：`rag_tutorial`
- Collection：`hierarchical_docs`（避免覆盖已有 `docs`）

## 运行

先确保项目根目录 `.env` 包含 `SILICONFLOW_API_KEY` 和 `SILICONFLOW_BASE_URL`，且 Milvus 已启动：

```bash
python 08-rag/chunk_strategy/hierarchical_embedding.py knowledge.txt
```

自定义参数：

```bash
python 08-rag/chunk_strategy/hierarchical_embedding.py knowledge.txt \
  --chunk-size 500 \
  --chunk-overlap 80 \
  --collection hierarchical_docs
```

代码中复用已有对象：

```python
pipeline = HierarchicalEmbeddingPipeline(
    embeddings=embeddings,
    milvus_client=client,
    db_name="rag_tutorial",
    collection_name="hierarchical_docs",
)
chunks = pipeline.ingest_file("knowledge.txt")
```

父块用于保留完整章节语义；子块用于精确检索。每个子块通过 `parent_id` 指向父块，`header_path` 保存完整标题路径。实际向量化使用 `embedding_text`（标题路径 + 父级上下文 + 当前内容），Milvus 中的 `text` 则保留未经增强的原始块，便于生成回答时引用。
