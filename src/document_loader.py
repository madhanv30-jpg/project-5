from pathlib import Path
from langchain_core.documents import Document
import re

from config import DOCS_DIR


def load_markdown_docs(docs_dir: Path = DOCS_DIR) -> list[Document]:
    docs = []
    for md_file in sorted(docs_dir.rglob("*.md")):
        content = md_file.read_text(encoding="utf-8")
        relative_path = md_file.relative_to(docs_dir)
        metadata = {
            "source": str(relative_path),
            "file_name": md_file.name,
        }
        title_match = re.search(r"^#\s+(.+)$", content, re.MULTILINE)
        if title_match:
            metadata["title"] = title_match.group(1).strip()
        docs.append(Document(page_content=content, metadata=metadata))
    return docs
