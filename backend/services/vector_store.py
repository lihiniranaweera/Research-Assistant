"""FAISS-backed vector store manager with per-collection persistence."""
from __future__ import annotations

import json
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from langchain_community.vectorstores import FAISS
from langchain_core.documents import Document
from langchain_openai import OpenAIEmbeddings

from backend.config import get_settings
from backend.models.schemas import CollectionInfo, DocumentMeta


def _embeddings() -> OpenAIEmbeddings:
    settings = get_settings()
    return OpenAIEmbeddings(
        model=settings.embedding_model,
        openai_api_key=settings.openai_api_key,
    )


def _collection_dir(name: str) -> Path:
    settings = get_settings()
    return Path(settings.data_dir) / name


def _meta_path(name: str) -> Path:
    return _collection_dir(name) / "metadata.json"


def _load_meta(name: str) -> dict:
    p = _meta_path(name)
    if not p.exists():
        raise KeyError(f"Collection '{name}' not found")
    return json.loads(p.read_text())


def _save_meta(name: str, meta: dict) -> None:
    _meta_path(name).write_text(json.dumps(meta, indent=2))


def create_collection(name: str, description: str = "") -> CollectionInfo:
    col_dir = _collection_dir(name)
    if col_dir.exists():
        raise ValueError(f"Collection '{name}' already exists")
    col_dir.mkdir(parents=True)
    meta = {
        "name": name,
        "description": description,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "documents": [],
    }
    _save_meta(name, meta)
    return _meta_to_info(meta)


def list_collections() -> list[CollectionInfo]:
    settings = get_settings()
    base = Path(settings.data_dir)
    base.mkdir(parents=True, exist_ok=True)
    infos = []
    for p in sorted(base.iterdir()):
        if p.is_dir() and (p / "metadata.json").exists():
            try:
                infos.append(_meta_to_info(_load_meta(p.name)))
            except Exception:
                pass
    return infos


def get_collection(name: str) -> CollectionInfo:
    return _meta_to_info(_load_meta(name))


def delete_collection(name: str) -> None:
    col_dir = _collection_dir(name)
    if not col_dir.exists():
        raise KeyError(f"Collection '{name}' not found")
    shutil.rmtree(col_dir)


def add_documents(collection_name: str, doc_id: str, filename: str, chunks: list[Document]) -> int:
    meta = _load_meta(collection_name)
    col_dir = _collection_dir(collection_name)
    faiss_dir = col_dir / "faiss"
    emb = _embeddings()

    if faiss_dir.exists():
        store = FAISS.load_local(str(faiss_dir), emb, allow_dangerous_deserialization=True)
        store.add_documents(chunks)
    else:
        store = FAISS.from_documents(chunks, emb)

    store.save_local(str(faiss_dir))
    meta["documents"].append({
        "doc_id": doc_id,
        "filename": filename,
        "num_chunks": len(chunks),
        "uploaded_at": datetime.now(timezone.utc).isoformat(),
    })
    _save_meta(collection_name, meta)
    return len(chunks)


def delete_document(collection_name: str, doc_id: str) -> None:
    """Remove a document's chunks by rebuilding the FAISS index without them."""
    meta = _load_meta(collection_name)
    doc_entry = next((d for d in meta["documents"] if d["doc_id"] == doc_id), None)
    if doc_entry is None:
        raise KeyError(f"Document '{doc_id}' not found in collection '{collection_name}'")

    col_dir = _collection_dir(collection_name)
    faiss_dir = col_dir / "faiss"
    emb = _embeddings()

    remaining: list[Document] = []
    if faiss_dir.exists():
        store = FAISS.load_local(str(faiss_dir), emb, allow_dangerous_deserialization=True)
        all_docs = list(store.docstore._dict.values())
        remaining = [d for d in all_docs if d.metadata.get("doc_id") != doc_id]

    shutil.rmtree(faiss_dir, ignore_errors=True)
    if remaining:
        new_store = FAISS.from_documents(remaining, emb)
        new_store.save_local(str(faiss_dir))

    meta["documents"] = [d for d in meta["documents"] if d["doc_id"] != doc_id]
    _save_meta(collection_name, meta)


def get_retriever(collection_name: str, k: Optional[int] = None):
    settings = get_settings()
    k = k or settings.max_retrieval_docs
    col_dir = _collection_dir(collection_name)
    faiss_dir = col_dir / "faiss"
    if not faiss_dir.exists():
        raise ValueError(f"Collection '{collection_name}' has no indexed documents yet")
    emb = _embeddings()
    store = FAISS.load_local(str(faiss_dir), emb, allow_dangerous_deserialization=True)
    return store.as_retriever(search_kwargs={"k": k})


def similarity_search_with_score(collection_name: str, query: str, k: int = 6):
    col_dir = _collection_dir(collection_name)
    faiss_dir = col_dir / "faiss"
    if not faiss_dir.exists():
        return []
    emb = _embeddings()
    store = FAISS.load_local(str(faiss_dir), emb, allow_dangerous_deserialization=True)
    return store.similarity_search_with_relevance_scores(query, k=k)


def _meta_to_info(meta: dict) -> CollectionInfo:
    docs = [DocumentMeta(**d) for d in meta.get("documents", [])]
    return CollectionInfo(
        name=meta["name"],
        description=meta.get("description", ""),
        created_at=meta["created_at"],
        document_count=len(docs),
        documents=docs,
    )
