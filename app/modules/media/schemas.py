from pydantic import BaseModel


class FileUploadResponse(BaseModel):
    filename: str
    url: str
    content_type: str
    size_bytes: int
