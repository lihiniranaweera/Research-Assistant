from fastapi import APIRouter, Depends, File, HTTPException, Query, UploadFile, status

from backend.auth import require_api_key
from backend.models.schemas import CollectionInfo, DeleteDocumentResponse, UploadResponse
from backend.services import document_processor as dp
from backend.services import vector_store as vs

router = APIRouter(prefix="/documents", tags=["documents"])

ALLOWED_EXTENSIONS = {".pdf", ".txt", ".md", ".html", ".htm"}


@router.post("/upload", response_model=UploadResponse, status_code=status.HTTP_201_CREATED)
async def upload_document(
    file: UploadFile = File(...),
    collection: str = Query(..., description="Target collection name"),
    _: str = Depends(require_api_key),
):
    ext = "." + (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}",
        )

    try:
        vs.get_collection(collection)
    except KeyError:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Collection '{collection}' not found")

    data = await file.read()
    try:
        doc_id, chunks = dp.process_upload(file.filename or "upload", data)
    except Exception as e:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail=f"Failed to parse file: {e}")

    if not chunks:
        raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_ENTITY, detail="Document produced no text content")

    num_chunks = vs.add_documents(collection, doc_id, file.filename or "upload", chunks)

    return UploadResponse(
        collection=collection,
        doc_id=doc_id,
        filename=file.filename or "upload",
        num_chunks=num_chunks,
        message=f"Successfully indexed {num_chunks} chunks",
    )


@router.get("", response_model=CollectionInfo)
async def list_documents(
    collection: str = Query(..., description="Collection name"),
    _: str = Depends(require_api_key),
):
    try:
        return vs.get_collection(collection)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{doc_id}", response_model=DeleteDocumentResponse)
async def delete_document(
    doc_id: str,
    collection: str = Query(..., description="Collection name"),
    _: str = Depends(require_api_key),
):
    try:
        vs.delete_document(collection, doc_id)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    return DeleteDocumentResponse(collection=collection, doc_id=doc_id, message="Document removed")
