import io
import os
import uuid

from fastapi import HTTPException, UploadFile, status
from PIL import Image, ImageOps

from app.core.config import settings

ALLOWED_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".jfif",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
    ".avif",
    ".mp3",
    ".wav",
    ".ogg",
    ".m4a",
}
IMAGE_EXTENSIONS = {
    ".jpg",
    ".jpeg",
    ".png",
    ".gif",
    ".webp",
    ".jfif",
    ".bmp",
    ".tiff",
    ".tif",
    ".heic",
    ".heif",
    ".avif",
}
MAX_FILE_SIZE = 25 * 1024 * 1024  # 25 MB
CHUNK_SIZE = 64 * 1024


def ensure_upload_dir_exists() -> str:
    upload_path = os.path.abspath(settings.UPLOAD_DIR)
    os.makedirs(upload_path, exist_ok=True)
    return upload_path


def public_url_for(filename: str) -> str:
    """Absolute URL: the browser loads these from a different origin than the
    frontend, so a bare '/uploads/...' would resolve against the app instead."""
    return f"{settings.PUBLIC_API_URL.rstrip('/')}/uploads/{filename}"


def _optimize_and_save_image(
    file_bytes: bytes,
    original_ext: str,
    upload_dir: str,
    clean_stem: str,
) -> tuple[str, int]:
    """Auto-orient, resize if too large, and compress images with PIL."""
    try:
        with Image.open(io.BytesIO(file_bytes)) as img:
            # Auto-rotate according to EXIF tags (fixes mobile photo orientation)
            try:
                transposed = ImageOps.exif_transpose(img)
                if transposed is not None:
                    img = transposed
            except Exception:
                pass

            # Check if animated GIF: keep as-is
            is_animated = getattr(img, "is_animated", False)
            if is_animated and original_ext == ".gif":
                unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_stem}.gif"
                file_path = os.path.join(upload_dir, unique_filename)
                with open(file_path, "wb") as buffer:
                    buffer.write(file_bytes)
                return unique_filename, len(file_bytes)

            # Resize if dimensions exceed 2048px on longest side
            max_dim = 2048
            w, h = img.size
            if w > max_dim or h > max_dim:
                if w > h:
                    new_h = max(1, int((h * max_dim) / w))
                    new_w = max_dim
                else:
                    new_w = max(1, int((w * max_dim) / h))
                    new_h = max_dim
                resample = getattr(getattr(Image, "Resampling", Image), "LANCZOS", Image.LANCZOS)
                img = img.resize((new_w, new_h), resample=resample)

            has_alpha = img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info)

            if has_alpha:
                unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_stem}.webp"
                file_path = os.path.join(upload_dir, unique_filename)
                img.save(file_path, format="WEBP", quality=88, method=4)
            else:
                if img.mode != "RGB":
                    img = img.convert("RGB")
                unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_stem}.jpg"
                file_path = os.path.join(upload_dir, unique_filename)
                img.save(file_path, format="JPEG", quality=85, optimize=True)

            return unique_filename, os.path.getsize(file_path)
    except Exception:
        # Fallback to direct raw write if PIL cannot parse
        unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_stem}{original_ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        return unique_filename, len(file_bytes)


async def save_uploaded_file(file: UploadFile) -> tuple[str, str, int]:
    # basename() first to prevent directory traversal
    raw_name = os.path.basename(file.filename or "file.bin").replace("\\", "_")
    name_stem, ext = os.path.splitext(raw_name)
    ext = ext.lower()
    clean_stem = name_stem.replace(" ", "_") or "upload"

    if ext not in ALLOWED_EXTENSIONS:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            f"Unsupported file format '{ext}'. Allowed: {', '.join(sorted(ALLOWED_EXTENSIONS))}",
        )

    upload_dir = ensure_upload_dir_exists()

    # Read chunks into memory up to MAX_FILE_SIZE
    size = 0
    chunks: list[bytes] = []
    try:
        while chunk := await file.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_FILE_SIZE:
                raise HTTPException(
                    status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                    "File exceeds the 25MB limit.",
                )
            chunks.append(chunk)
    finally:
        await file.close()

    file_bytes = b"".join(chunks)

    if ext in IMAGE_EXTENSIONS:
        unique_filename, final_size = _optimize_and_save_image(
            file_bytes, ext, upload_dir, clean_stem
        )
    else:
        unique_filename = f"{uuid.uuid4().hex[:12]}_{clean_stem}{ext}"
        file_path = os.path.join(upload_dir, unique_filename)
        with open(file_path, "wb") as buffer:
            buffer.write(file_bytes)
        final_size = len(file_bytes)

    file_path = os.path.join(upload_dir, unique_filename)
    # Defence in depth: refuse anything that still resolves outside the dir.
    if os.path.commonpath([upload_dir, os.path.abspath(file_path)]) != upload_dir:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Invalid filename.")

    return unique_filename, public_url_for(unique_filename), final_size
