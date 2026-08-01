import os
import uuid

from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".mp3", ".wav"}
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB
CHUNK_SIZE = 64 * 1024


def ensure_upload_dir_exists() -> str:
    upload_path = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def public_url_for(filename: str) -> str:
    """Absolute URL: the browser loads these from a different origin than the
    frontend, so a bare '/uploads/...' would resolve against the app instead."""
    return f"{settings.PUBLIC_API_URL.rstrip('/')}/uploads/{filename}"


async def save_uploaded_file(file: UploadFile) -> tuple[str, str, int]:
    # basename() first. The client controls this string, and without it a name
    # like "../../../pwned.png" passes the extension check and escapes the
    # upload directory -- the uuid prefix does not neutralise a "../".
    raw_name = os.path.basename(file.filename or "file.bin").replace("\\", "_")
    ext = os.path.splitext(raw_name)[1].lower()

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    upload_dir = ensure_upload_dir_exists()
    unique_filename = f"{uuid.uuid4().hex[:12]}_{raw_name.replace(' ', '_')}"
    file_path = os.path.join(upload_dir, unique_filename)

    # Defence in depth: refuse anything that still resolves outside the dir.
    if os.path.commonpath([upload_dir, os.path.abspath(file_path)]) != upload_dir:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename.")

    # Stream, and abort the moment the cap is passed, instead of writing the
    # whole body to disk and measuring it afterwards. await file.read() also
    # keeps this off the event loop, unlike the previous shutil.copyfileobj.
    size = 0
    try:
        with open(file_path, "wb") as buffer:
            while chunk := await file.read(CHUNK_SIZE):
                size += len(chunk)
                if size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                        "File exceeds the 10MB limit.",
                    )
                buffer.write(chunk)
    except Exception:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    return unique_filename, public_url_for(unique_filename), size
