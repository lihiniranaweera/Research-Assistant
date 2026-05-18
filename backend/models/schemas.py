from __future__ import annotations

from datetime import datetime
from typing import Any
from pydantic import BaseModel, Field


# ── Collections ──────────────────────────────────────────────────────────────

class CollectionCreate(BaseModel):
    name: str = Field(..., pattern=r"^[a-zA-Z0-9_\-]+$", description="Alphanumeric name (no spaces)")
    description: str = ""


class DocumentMeta(BaseModel):
    doc_id: str
    filename: str
    num_chunks: int
    uploaded_at: str


class CollectionInfo(BaseModel):
    name: str
    description: str
    created_at: str
    document_count: int
    documents: list[DocumentMeta] = []


class CollectionList(BaseModel):
    collections: list[CollectionInfo]


# ── Documents ─────────────────────────────────────────────────────────────────

class UploadResponse(BaseModel):
    collection: str
    doc_id: str
    filename: str
    num_chunks: int
    message: str


class DeleteDocumentResponse(BaseModel):
    collection: str
    doc_id: str
    message: str


# ── Chat ──────────────────────────────────────────────────────────────────────

class ChatMessage(BaseModel):
    role: str  # "human" | "assistant"
    content: str


class ChatRequest(BaseModel):
    session_id: str = Field(..., description="Client-generated session identifier")
    collection: str = Field(..., description="Name of the collection to query against")
    message: str
    stream: bool = False


class SourceDocument(BaseModel):
    doc_id: str
    filename: str
    page_content: str
    score: float | None = None
    metadata: dict[str, Any] = {}


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    sources: list[SourceDocument] = []
    tool_calls_made: list[str] = []


# ── Health ────────────────────────────────────────────────────────────────────

class HealthResponse(BaseModel):
    status: str
    version: str = "1.0.0"
    timestamp: str = Field(default_factory=lambda: datetime.utcnow().isoformat())
