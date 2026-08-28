import hashlib
from pinecone import Pinecone, ServerlessSpec
from langchain_openai import OpenAIEmbeddings
from langchain_pinecone import PineconeVectorStore
from rank_bm25 import BM25Okapi
from langchain_core.documents import Document

from config import (
    PINECONE_API_KEY,
    PINECONE_INDEX_NAME,
    EMBEDDING_MODEL,
    EMBEDDING_PROVIDER,
    LOCAL_EMBEDDING_MODEL,
    EMBED_DIM,
    DOCS_DIR,
)


def _make_embeddings():
    if EMBEDDING_PROVIDER == "local":
        try:
            from langchain_huggingface import HuggingFaceEmbeddings
        except Exception:  # noqa: BLE001
            try:
                from langchain_community.embeddings import HuggingFaceEmbeddings
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    "EMBEDDING_PROVIDER=local requires 'sentence-transformers' installed "
                    f"(pip install -r requirements-local.txt). Got: {exc}"
                ) from exc
        return HuggingFaceEmbeddings(model_name=LOCAL_EMBEDDING_MODEL)
    return OpenAIEmbeddings(model=EMBEDDING_MODEL)


embeddings = _make_embeddings()

_bm25_corpus: list[str] = []
_bm25_metadata: list[dict] = []
_bm25_index: BM25Okapi | None = None

_doc_registry: dict[str, dict] = {}


def get_pinecone_index():
    pc = Pinecone(api_key=PINECONE_API_KEY)
    existing = [idx.name for idx in pc.list_indexes()]
    if PINECONE_INDEX_NAME not in existing:
        pc.create_index(
            name=PINECONE_INDEX_NAME,
            dimension=EMBED_DIM,
            metric="cosine",
            spec=ServerlessSpec(cloud="aws", region="us-east-1"),
        )
    return pc.Index(PINECONE_INDEX_NAME)


def get_vector_store() -> PineconeVectorStore:
    index = get_pinecone_index()
    return PineconeVectorStore(
        index=index,
        embedding=embeddings,
        text_key="text",
        namespace="docs",
    )


def _stable_id(content: str) -> str:
    return "chunk-" + hashlib.md5(content.encode("utf-8")).hexdigest()[:24]


def embed_documents(chunks: list[Document]):
    if not chunks:
        return
    vector_store = get_vector_store()
    ids = [_stable_id(c.page_content) for c in chunks]
    vector_store.add_documents(chunks, ids=ids)


def build_bm25_index(chunks: list[Document]):
    global _bm25_corpus, _bm25_metadata, _bm25_index, _doc_registry
    _bm25_corpus = [c.page_content.lower() for c in chunks]
    _bm25_metadata = [c.metadata for c in chunks]
    tokenized = [doc.split() for doc in _bm25_corpus]
    _bm25_index = BM25Okapi(tokenized)
    _doc_registry = {}
    for c in chunks:
        src = c.metadata.get("source", "unknown")
        _doc_registry.setdefault(src, {"source": src, "title": c.metadata.get("title", ""), "chunks": 0})
        _doc_registry[src]["chunks"] += 1


def keyword_search(query: str, k: int = 5) -> list[dict]:
    if _bm25_index is None:
        return []
    tokenized_query = query.lower().split()
    scores = _bm25_index.get_scores(tokenized_query)
    top_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)[:k]
    results = []
    for idx in top_indices:
        if scores[idx] > 0:
            results.append({
                "content": _bm25_corpus[idx],
                "metadata": _bm25_metadata[idx],
                "score": float(scores[idx]),
                "type": "keyword",
            })
    return results


def semantic_search(query: str, k: int = 5) -> list[dict]:
    vector_store = get_vector_store()
    semantic_results = vector_store.similarity_search_with_score(query, k=k)
    return [
        {
            "content": doc.page_content,
            "metadata": doc.metadata,
            "score": float(score),
            "type": "semantic",
        }
        for doc, score in semantic_results
    ]


def hybrid_search(query: str, k: int = 5) -> list[dict]:
    semantic_hits = semantic_search(query, k=k * 2)
    keyword_hits = keyword_search(query, k=k * 2)

    seen = set()
    merged = []
    for hit in semantic_hits + keyword_hits:
        key = hit["content"][:200]
        if key not in seen:
            seen.add(key)
            merged.append(hit)

    for hit in merged:
        hit["final_score"] = hit["score"] if hit["type"] == "semantic" else hit["score"] * 0.3

    merged.sort(key=lambda x: x["final_score"], reverse=True)
    return merged[:k]


def list_documents() -> list[dict]:
    if _doc_registry:
        return list(_doc_registry.values())
    docs = []
    for md_file in sorted(DOCS_DIR.rglob("*.md")):
        rel = str(md_file.relative_to(DOCS_DIR))
        docs.append({"source": rel, "title": md_file.stem, "chunks": None})
    return docs


def get_document(source: str) -> str:
    target = DOCS_DIR / source
    if not target.exists():
        for md_file in DOCS_DIR.rglob("*.md"):
            if md_file.name == source or str(md_file.relative_to(DOCS_DIR)) == source:
                target = md_file
                break
    if not target.exists():
        return f"Document '{source}' not found in the knowledge base."
    return target.read_text(encoding="utf-8")
