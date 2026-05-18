from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_api_key
from backend.models.schemas import ChatRequest, ChatResponse, SourceDocument
from backend.services import memory as mem
from backend.services import vector_store as vs
from backend.services.agent import run_agent

router = APIRouter(prefix="/chat", tags=["chat"])


@router.post("", response_model=ChatResponse)
async def chat(
    body: ChatRequest,
    _: str = Depends(require_api_key),
):
    try:
        info = vs.get_collection(body.collection)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{body.collection}' not found")

    if info.document_count == 0:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Collection has no documents. Upload at least one document before chatting.",
        )

    history = mem.get_history(body.session_id)

    try:
        result = run_agent(body.collection, body.message, history)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail=f"Agent error: {e}")

    answer = result["answer"]
    mem.append_exchange(body.session_id, body.message, answer)

    sources: list[SourceDocument] = []
    try:
        raw = vs.similarity_search_with_score(body.collection, body.message, k=3)
        for doc, score in raw:
            sources.append(
                SourceDocument(
                    doc_id=doc.metadata.get("doc_id", ""),
                    filename=doc.metadata.get("filename", ""),
                    page_content=doc.page_content[:400],
                    score=round(score, 4),
                    metadata=doc.metadata,
                )
            )
    except Exception:
        pass

    return ChatResponse(
        session_id=body.session_id,
        answer=answer,
        sources=sources,
        tool_calls_made=result.get("tool_calls_made", []),
    )


@router.delete("/sessions/{session_id}", status_code=status.HTTP_204_NO_CONTENT)
async def clear_session(session_id: str, _: str = Depends(require_api_key)):
    mem.clear_history(session_id)
