"""Parse uploaded files into LangChain Documents and split them into chunks."""
from __future__ import annotations

import io
import uuid
from pathlib import Path

from bs4 import BeautifulSoup
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from pypdf import PdfReader

from backend.config import get_settings

SUPPORTED_EXTENSIONS = {".pdf", ".txt", ".md", ".html", ".htm"}


def _load_pdf(data: bytes) -> str:
    reader = PdfReader(io.BytesIO(data))
    return "\n\n".join(page.extract_text() or "" for page in reader.pages)


def _load_html(data: bytes) -> str:
    soup = BeautifulSoup(data, "lxml")
    for tag in soup(["script", "style", "nav", "footer", "header"]):
        tag.decompose()
    return soup.get_text(separator="\n", strip=True)


def _load_text(data: bytes) -> str:
    return data.decode("utf-8", errors="replace")


def parse_file(filename: str, data: bytes) -> str:
    ext = Path(filename).suffix.lower()
    if ext == ".pdf":
        return _load_pdf(data)
    if ext in {".html", ".htm"}:
        return _load_html(data)
    if ext in {".txt", ".md"}:
        return _load_text(data)
    raise ValueError(f"Unsupported file type: {ext}")


def chunk_text(text: str, filename: str, doc_id: str) -> list[Document]:
    settings = get_settings()
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = splitter.split_text(text)
    return [
        Document(
            page_content=chunk,
            metadata={"doc_id": doc_id, "filename": filename, "chunk_index": i},
        )
        for i, chunk in enumerate(chunks)
        if chunk.strip()
    ]


def process_upload(filename: str, data: bytes) -> tuple[str, list[Document]]:
    """Return (doc_id, chunks)."""
    doc_id = str(uuid.uuid4())
    raw_text = parse_file(filename, data)
    chunks = chunk_text(raw_text, filename, doc_id)
    return doc_id, chunks
