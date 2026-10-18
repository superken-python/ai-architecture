"""Knowledge (RAG) — Agno `Knowledge` + `search_knowledge=True` ↔ vector store + một tool tìm kiếm.

| Agno | LangChain |
|---|---|
| `kb.insert(name=..., upsert=True)` | `store.add_documents(docs, ids=[...])` — cùng id thì ghi đè |
| `kb.remove_vectors_by_name(name)` | `store.delete(ids=[...])` |
| `kb.search(q, filters={"source": ...})` | `store.similarity_search(q, k, filter=lambda d: ...)` |
| `search_knowledge=True` → tool `search_knowledge_base` | tự viết tool gọi `similarity_search` |

`InMemoryVectorStore` cần numpy. `KeywordEmbeddings` băm từ khoá (giống `/v1/embeddings` của mock_llm ở lab Agno):
câu chung từ khoá thì gần nhau — đủ để học luồng offline, không phải semantic thật. Production: OpenAIEmbeddings,
Ollama... và vector DB có lưu bền (pgvector, LanceDB, Qdrant).
"""

from __future__ import annotations

import hashlib
import math
import re

from langchain.tools import BaseTool, tool
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.vectorstores import InMemoryVectorStore

POLICIES: dict[str, tuple[str, dict]] = {  # id ổn định → (nội dung, metadata)
    "no-90": ("Nợ trên 90% hạn mức tín dụng: tạm dừng giao hàng mới, báo trưởng phòng tín dụng.", {"source": "policy"}),
    "no-qua-han": ("Nợ quá hạn 30 ngày: gửi thư nhắc nợ lần một, sau 60 ngày gọi điện.", {"source": "policy"}),
    "thu-nhac-no": ("Thư nhắc nợ phải nêu tên khách hàng, số tiền nợ và hạn thanh toán.", {"source": "style"}),
}


class KeywordEmbeddings(Embeddings):
    def __init__(self, dims: int = 256) -> None:
        self.dims = dims

    def _embed(self, text: str) -> list[float]:
        vector = [0.0] * self.dims
        for word in re.findall(r"\w+", text.lower()):
            vector[int(hashlib.md5(word.encode()).hexdigest(), 16) % self.dims] += 1.0
        norm = math.sqrt(sum(v * v for v in vector)) or 1.0
        return [v / norm for v in vector]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


def index(store: InMemoryVectorStore, docs: dict[str, tuple[str, dict]]) -> dict[str, int]:
    """Đồng bộ store với nguồn: ghi đè theo id, xoá id đã biến mất khỏi nguồn."""
    removed = [doc_id for doc_id in store.store if doc_id not in docs]
    if removed:
        store.delete(ids=removed)
    store.add_documents([Document(page_content=text, metadata=meta) for text, meta in docs.values()], ids=list(docs))
    return {"upserted": len(docs), "removed": len(removed)}


def make_policy_tool(store: InMemoryVectorStore) -> BaseTool:
    @tool
    def search_policies(query: str) -> str:
        """Tìm chính sách công nợ của công ty (chỉ chính sách, không có số liệu khách hàng)."""
        hits = store.similarity_search(query, k=2, filter=lambda doc: doc.metadata["source"] == "policy")
        return "\n".join(f"[{doc.id}] {doc.page_content}" for doc in hits) or "Không tìm thấy chính sách phù hợp."

    return search_policies
