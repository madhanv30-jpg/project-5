"""
Standalone knowledge-base ingestion script.

Reads every markdown file under docs/, chunks it, embeds it into the Pinecone
index, and builds the in-memory BM25 keyword index.

Usage:
    D:\\madhan\\project\\maddy\\venv\\Scripts\\python.exe ingest.py            # normal (adds/updates)
    D:\\madhan\\project\\maddy\\venv\\Scripts\\python.exe ingest.py --fresh   # wipe vectors first, then re-ingest
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import PINECONE_INDEX_NAME
from src.knowledge_base import init_knowledge_base
from src.document_loader import load_markdown_docs


def clear_index_namespace():
    """Delete all existing vectors so the index exactly matches docs/."""
    from src.embedder import get_pinecone_index
    index = get_pinecone_index()
    index.delete(delete_all=True, namespace="docs")
    print("[ingest] Cleared existing vectors from namespace 'docs'.")


def main():
    fresh = "--fresh" in sys.argv

    docs = load_markdown_docs()
    if not docs:
        print('[ingest] No markdown files found under docs/. Nothing to do.')
        sys.exit(1)

    print(f"[ingest] Found {len(docs)} markdown file(s):")
    for d in docs:
        print(f"          - {d.metadata['source']}")

    if fresh:
        clear_index_namespace()

    chunks = init_knowledge_base()
    print(f"[ingest] Embedded {chunks} chunks into Pinecone index '{PINECONE_INDEX_NAME}'.")
    print("[ingest] BM25 keyword index rebuilt in memory.")
    print("[ingest] Done.")


if __name__ == "__main__":
    main()
