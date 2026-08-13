"""分层文档切块、上下文增强、Embedding 与 Milvus 入库。

处理链路对应设计图：
原始文档 -> 文档分析 -> 文档树 -> 分层切块 -> 上下文增强 ->
Chunk Metadata -> Parent-Child Mapping -> Embedding -> Milvus。

核心流水线通过依赖注入接收 LangChain Embeddings 与 MilvusClient，因此既能
复用项目已有实例，也便于在不访问外部服务时进行单元测试。
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Iterable, Protocol, Sequence


class EmbeddingsLike(Protocol):
    def embed_documents(self, texts: list[str]) -> list[list[float]]: ...


class MilvusClientLike(Protocol):
    def list_databases(self) -> list[str]: ...
    def create_database(self, db_name: str) -> Any: ...
    def use_database(self, db_name: str) -> Any: ...
    def has_collection(self, collection_name: str) -> bool: ...
    def create_collection(self, **kwargs: Any) -> Any: ...
    def upsert(self, **kwargs: Any) -> Any: ...
    def flush(self, collection_name: str) -> Any: ...


@dataclass(frozen=True)
class ChunkConfig:
    """切块参数，长度单位为字符。"""

    chunk_size: int = 500
    chunk_overlap: int = 80
    parent_context_size: int = 220
    batch_size: int = 32

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError("chunk_size 必须大于 0")
        if not 0 <= self.chunk_overlap < self.chunk_size:
            raise ValueError("chunk_overlap 必须满足 0 <= overlap < chunk_size")
        if self.parent_context_size < 0 or self.batch_size <= 0:
            raise ValueError("parent_context_size 不能为负，batch_size 必须大于 0")


@dataclass
class DocumentSection:
    """文档分析器生成的树节点。"""

    title: str
    level: int
    header_path: list[str]
    content: str = ""
    start_index: int = 0
    children: list["DocumentSection"] = field(default_factory=list)


@dataclass
class HierarchicalChunk:
    """可写入向量库的父块或子块。"""

    id: int
    chunk_id: str
    doc_id: str
    parent_id: str
    chunk_type: str
    level: int
    header_path: list[str]
    text: str
    embedding_text: str
    source: str
    start_index: int
    end_index: int

    def metadata(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("embedding_text")
        serialized_path = json.dumps(self.header_path, ensure_ascii=False)
        data["header_path"] = serialized_path
        # 同时提供设计图中的 camelCase 字段名，方便与已有前端/接口对接。
        data["headerPath"] = serialized_path
        return data


_HEADING_RE = re.compile(r"^(#{1,6})\s+(.+?)\s*$", re.MULTILINE)
_BOUNDARY_RE = re.compile(r"\n\n+|(?<=[。！？!?；;])|\n")


def _stable_id(value: str) -> int:
    """生成适合 Milvus INT64 主键的稳定正整数。"""

    return int.from_bytes(hashlib.sha256(value.encode("utf-8")).digest()[:8], "big") & ((1 << 63) - 1)


def _doc_id(source: str, text: str) -> str:
    payload = f"{source}\0{text}".encode("utf-8")
    return hashlib.sha256(payload).hexdigest()[:24]


def analyze_document(text: str) -> DocumentSection:
    """分析 Markdown 标题并构建文档树；普通文本会成为根节点内容。"""

    root = DocumentSection(title="文档", level=0, header_path=[])
    matches = list(_HEADING_RE.finditer(text))
    if not matches:
        root.content = text.strip()
        return root

    preface = text[: matches[0].start()].strip()
    root.content = preface
    stack: list[DocumentSection] = [root]
    for index, match in enumerate(matches):
        level = len(match.group(1))
        title = match.group(2).strip()
        content_start = match.end()
        content_end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        while stack[-1].level >= level:
            stack.pop()
        parent = stack[-1]
        node = DocumentSection(
            title=title,
            level=level,
            header_path=[*parent.header_path, title],
            content=text[content_start:content_end].strip(),
            start_index=content_start,
        )
        parent.children.append(node)
        stack.append(node)
    return root


def _split_text(text: str, size: int, overlap: int) -> list[tuple[str, int, int]]:
    """优先在段落和中文标点处切分，并返回相对位置。"""

    text = text.strip()
    if not text:
        return []
    chunks: list[tuple[str, int, int]] = []
    start = 0
    while start < len(text):
        hard_end = min(start + size, len(text))
        end = hard_end
        if hard_end < len(text):
            candidates = [m.end() for m in _BOUNDARY_RE.finditer(text, start, hard_end)]
            # 避免选择过于靠前的分隔点，导致产生大量小块。
            useful = [pos for pos in candidates if pos >= start + size // 2]
            if useful:
                end = useful[-1]
        chunk = text[start:end].strip()
        if chunk:
            actual_start = text.find(chunk, start, end)
            chunks.append((chunk, actual_start, actual_start + len(chunk)))
        if end >= len(text):
            break
        next_start = max(start + 1, end - overlap)
        start = next_start
    return chunks


def _iter_sections(root: DocumentSection) -> Iterable[DocumentSection]:
    yield root
    for child in root.children:
        yield from _iter_sections(child)


class HierarchicalEmbeddingPipeline:
    def __init__(
        self,
        embeddings: EmbeddingsLike,
        milvus_client: MilvusClientLike,
        *,
        db_name: str = "rag_tutorial",
        collection_name: str = "hierarchical_docs",
        config: ChunkConfig | None = None,
    ) -> None:
        self.embeddings = embeddings
        self.client = milvus_client
        self.db_name = db_name
        self.collection_name = collection_name
        self.config = config or ChunkConfig()

    def create_chunks(self, text: str, *, source: str = "unknown") -> list[HierarchicalChunk]:
        """创建含标题继承、增强上下文和父子映射的块。"""

        root = analyze_document(text)
        document_id = _doc_id(source, text)
        chunks: list[HierarchicalChunk] = []

        for section_no, section in enumerate(_iter_sections(root)):
            if not section.content:
                continue
            path_text = " > ".join(section.header_path) or "文档正文"
            parent_key = f"{document_id}:section:{section_no}:{path_text}"
            parent_chunk_id = hashlib.sha256(parent_key.encode()).hexdigest()[:24]
            # 父块是章节级概览，控制长度以免超出 Embedding 模型上下文窗口；
            # 完整章节仍会被下方的所有子块覆盖。
            parent_text = section.content[: max(self.config.chunk_size, self.config.parent_context_size)]
            parent = HierarchicalChunk(
                id=_stable_id(parent_chunk_id),
                chunk_id=parent_chunk_id,
                doc_id=document_id,
                parent_id="",
                chunk_type="parent",
                level=section.level,
                header_path=section.header_path,
                text=parent_text,
                embedding_text=f"标题路径：{path_text}\n章节内容：{parent_text}",
                source=source,
                start_index=section.start_index,
                end_index=section.start_index + len(parent_text),
            )
            chunks.append(parent)

            parent_context = parent_text[: self.config.parent_context_size]
            for child_no, (child_text, rel_start, rel_end) in enumerate(
                _split_text(section.content, self.config.chunk_size, self.config.chunk_overlap)
            ):
                child_key = f"{parent_chunk_id}:child:{child_no}:{rel_start}"
                child_chunk_id = hashlib.sha256(child_key.encode()).hexdigest()[:24]
                enhanced = (
                    f"标题路径：{path_text}\n"
                    f"章节上下文：{parent_context}\n"
                    f"当前内容：{child_text}"
                )
                chunks.append(
                    HierarchicalChunk(
                        id=_stable_id(child_chunk_id),
                        chunk_id=child_chunk_id,
                        doc_id=document_id,
                        parent_id=parent_chunk_id,
                        chunk_type="child",
                        level=section.level + 1,
                        header_path=section.header_path,
                        text=child_text,
                        embedding_text=enhanced,
                        source=source,
                        start_index=section.start_index + rel_start,
                        end_index=section.start_index + rel_end,
                    )
                )
        return chunks

    def _embed(self, chunks: Sequence[HierarchicalChunk]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for start in range(0, len(chunks), self.config.batch_size):
            batch = chunks[start : start + self.config.batch_size]
            vectors.extend(self.embeddings.embed_documents([item.embedding_text for item in batch]))
        if len(vectors) != len(chunks):
            raise RuntimeError("Embedding 返回的向量数量与 chunk 数量不一致")
        return vectors

    def _ensure_collection(self, dimension: int) -> None:
        databases = self.client.list_databases()
        if self.db_name not in databases:
            self.client.create_database(db_name=self.db_name)
        self.client.use_database(db_name=self.db_name)
        if not self.client.has_collection(collection_name=self.collection_name):
            self.client.create_collection(
                collection_name=self.collection_name,
                dimension=dimension,
                metric_type="COSINE",
            )

    def ingest_text(self, text: str, *, source: str = "unknown") -> list[HierarchicalChunk]:
        chunks = self.create_chunks(text, source=source)
        if not chunks:
            return []
        vectors = self._embed(chunks)
        if not vectors or not vectors[0]:
            raise RuntimeError("Embedding 模型返回了空向量")
        dimension = len(vectors[0])
        if any(len(vector) != dimension for vector in vectors):
            raise RuntimeError("Embedding 向量维度不一致")
        self._ensure_collection(dimension)
        records = [
            {**chunk.metadata(), "vector": vector}
            for chunk, vector in zip(chunks, vectors)
        ]
        self.client.upsert(collection_name=self.collection_name, data=records)
        self.client.flush(collection_name=self.collection_name)
        return chunks

    def ingest_file(self, file_path: str | Path) -> list[HierarchicalChunk]:
        path = Path(file_path).expanduser().resolve()
        return self.ingest_text(path.read_text(encoding="utf-8"), source=str(path))


def build_default_pipeline(
    *,
    milvus_uri: str = "http://localhost:19530",
    db_name: str = "rag_tutorial",
    collection_name: str = "hierarchical_docs",
    config: ChunkConfig | None = None,
) -> HierarchicalEmbeddingPipeline:
    """使用项目现有 SiliconFlow BGE-M3 与 Milvus 配置构造流水线。"""

    from dotenv import load_dotenv
    from langchain.embeddings import init_embeddings
    from pymilvus import MilvusClient

    load_dotenv(override=True)
    api_key = os.getenv("SILICONFLOW_API_KEY")
    base_url = os.getenv("SILICONFLOW_BASE_URL")
    if not api_key or not base_url:
        raise RuntimeError("请在 .env 中配置 SILICONFLOW_API_KEY 和 SILICONFLOW_BASE_URL")
    embeddings = init_embeddings(
        model="openai:Pro/BAAI/bge-m3",
        api_key=api_key,
        base_url=base_url,
    )
    return HierarchicalEmbeddingPipeline(
        embeddings,
        MilvusClient(uri=milvus_uri),
        db_name=db_name,
        collection_name=collection_name,
        config=config,
    )


def main() -> None:
    parser = argparse.ArgumentParser(description="分层切块、向量化并写入 Milvus")
    parser.add_argument("file", help="待入库的 UTF-8 Markdown/TXT 文件")
    parser.add_argument("--milvus-uri", default="http://localhost:19530")
    parser.add_argument("--db", default="rag_tutorial")
    parser.add_argument("--collection", default="hierarchical_docs")
    parser.add_argument("--chunk-size", type=int, default=500)
    parser.add_argument("--chunk-overlap", type=int, default=80)
    args = parser.parse_args()
    pipeline = build_default_pipeline(
        milvus_uri=args.milvus_uri,
        db_name=args.db,
        collection_name=args.collection,
        config=ChunkConfig(chunk_size=args.chunk_size, chunk_overlap=args.chunk_overlap),
    )
    chunks = pipeline.ingest_file(args.file)
    parent_count = sum(chunk.chunk_type == "parent" for chunk in chunks)
    print(f"入库完成：{parent_count} 个父块，{len(chunks) - parent_count} 个子块")


if __name__ == "__main__":
    main()
