from fastapi import APIRouter, Depends, HTTPException, status

from backend.auth import require_api_key
from backend.models.schemas import CollectionCreate, CollectionInfo, CollectionList
from backend.services import vector_store as vs

router = APIRouter(prefix="/collections", tags=["collections"])


@router.post("", response_model=CollectionInfo, status_code=status.HTTP_201_CREATED)
async def create_collection(
    body: CollectionCreate,
    _: str = Depends(require_api_key),
):
    try:
        return vs.create_collection(body.name, body.description)
    except ValueError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))


@router.get("", response_model=CollectionList)
async def list_collections(_: str = Depends(require_api_key)):
    return CollectionList(collections=vs.list_collections())


@router.get("/{name}", response_model=CollectionInfo)
async def get_collection(name: str, _: str = Depends(require_api_key)):
    try:
        return vs.get_collection(name)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))


@router.delete("/{name}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_collection(name: str, _: str = Depends(require_api_key)):
    try:
        vs.delete_collection(name)
    except KeyError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
