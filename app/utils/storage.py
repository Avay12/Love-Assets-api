import os
import uuid
import shutil
from fastapi import UploadFile, HTTPException, status
from app.core.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp3", ".wav"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB limit


def ensure_upload_dir_exists() -> str:
    upload_path = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


async def save_uploaded_file(file: UploadFile) -> tuple[str, str, int]:
    filename = file.filename or "file.bin"
    ext = os.path.splitext(filename)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Unsupported file format '{ext}'. Allowed: {', '.join(ALLOWED_EXTENSIONS)}"
        )

    upload_dir = ensure_upload_dir_exists()
    unique_filename = f"{uuid.uuid4().hex[:12]}_{filename.replace(' ', '_')}"
    file_path = os.path.join(upload_dir, unique_filename)

    file_size = 0
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)
        file_size = os.path.getsize(file_path)

    if file_size > MAX_FILE_SIZE:
        os.remove(file_path)
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"File exceeds maximum size limit of 10MB."
        )

    public_url = f"/uploads/{unique_filename}"
    return unique_filename, public_url, file_size
