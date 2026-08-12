from fastapi import APIRouter, Depends, UploadFile, File, status

from app.core.deps import RateLimiter
from app.modules.media.schemas import FileUploadResponse
from app.utils.storage import save_uploaded_file

router = APIRouter()


@router.post(
    "/upload",
    response_model=FileUploadResponse,
    status_code=status.HTTP_201_CREATED,
    # Unauthenticated by design -- guests compose letters before signing up --
    # which also makes it an open write-to-disk endpoint. 60 files an hour per
    # IP is far above what composing a letter needs (12 photos maximum).
    dependencies=[Depends(RateLimiter(60, 3600, "upload"))],
    summary="Upload photo or media asset",
)
async def upload_media_file(
    file: UploadFile = File(...)
):
    filename, public_url, size_bytes = await save_uploaded_file(file)
    return FileUploadResponse(
        filename=filename,
        url=public_url,
        content_type=file.content_type or "application/octet-stream",
        size_bytes=size_bytes,
    )
