import unittest

from hierarchical_embedding import ChunkConfig, HierarchicalEmbeddingPipeline, analyze_document


class FakeEmbeddings:
    def embed_documents(self, texts):
        return [[float(len(text)), 1.0, 0.0] for text in texts]


class FakeMilvusClient:
    def __init__(self):
        self.databases = []
        self.collections = set()
        self.records = []

    def list_databases(self):
        return self.databases

    def create_database(self, db_name):
        self.databases.append(db_name)

    def use_database(self, db_name):
        self.db_name = db_name

    def has_collection(self, collection_name):
        return collection_name in self.collections

    def create_collection(self, **kwargs):
        self.collections.add(kwargs["collection_name"])
        self.dimension = kwargs["dimension"]

    def upsert(self, **kwargs):
        self.records.extend(kwargs["data"])

    def flush(self, collection_name):
        self.flushed = collection_name


class PipelineTest(unittest.TestCase):
    def setUp(self):
        self.client = FakeMilvusClient()
        self.pipeline = HierarchicalEmbeddingPipeline(
            FakeEmbeddings(),
            self.client,
            config=ChunkConfig(chunk_size=20, chunk_overlap=4, parent_context_size=10),
        )

    def test_document_tree_keeps_nested_header_path(self):
        root = analyze_document("# 产品\n介绍。\n## 价格\n价格说明。")
        self.assertEqual(root.children[0].header_path, ["产品"])
        self.assertEqual(root.children[0].children[0].header_path, ["产品", "价格"])

    def test_children_reference_parent_and_get_enhanced_context(self):
        chunks = self.pipeline.create_chunks(
            "# 产品\n这是一个比较长的产品说明，它包含功能、价格和使用方式。"
            "第二部分继续介绍部署、运维和常见问题。",
            source="demo.md",
        )
        parents = [item for item in chunks if item.chunk_type == "parent"]
        children = [item for item in chunks if item.chunk_type == "child"]
        self.assertEqual(len(parents), 1)
        self.assertGreaterEqual(len(children), 2)
        self.assertTrue(all(item.parent_id == parents[0].chunk_id for item in children))
        self.assertIn("标题路径：产品", children[0].embedding_text)
        self.assertIn("章节上下文：", children[0].embedding_text)

    def test_ingest_creates_collection_and_upserts_vectors(self):
        chunks = self.pipeline.ingest_text("# 标题\n正文内容。", source="demo.md")
        self.assertEqual(self.client.dimension, 3)
        self.assertEqual(len(self.client.records), len(chunks))
        self.assertTrue(all("vector" in record for record in self.client.records))
        child = next(record for record in self.client.records if record["chunk_type"] == "child")
        self.assertTrue(child["parent_id"])
        self.assertIn("标题", child["headerPath"])


if __name__ == "__main__":
    unittest.main()
