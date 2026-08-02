from typing import List, Optional
from pydantic import BaseModel, ConfigDict


class TemplateResponse(BaseModel):
    id: str
    title: str
    subtitle: str
    body: Optional[str] = None
    type: str
    experience: str
    image_url: Optional[str] = None
    is_premium: bool = False
    is_birthday_exclusive: bool = False

    model_config = ConfigDict(from_attributes=True)


class TemplateListResponse(BaseModel):
    total: int
    templates: List[TemplateResponse]
