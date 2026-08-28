from src.embedder import embed_documents, build_bm25_index
from src.document_loader import load_markdown_docs
from src.chunker import chunk_documents


def init_knowledge_base():
    docs = load_markdown_docs()
    if not docs:
        return 0
    chunks = chunk_documents(docs)
    embed_documents(chunks)
    build_bm25_index(chunks)
    return len(chunks)
