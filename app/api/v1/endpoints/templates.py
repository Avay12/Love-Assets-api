from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.schemas.template import TemplateResponse, TemplateListResponse
from app.services.template_service import TemplateService

router = APIRouter()


@router.get("/", response_model=TemplateListResponse, summary="List letter templates")
async def list_templates(
    type: Optional[str] = Query(None, description="Filter templates by type ('love' or 'birthday')"),
    db: AsyncSession = Depends(get_db)
):
    templates = await TemplateService.get_templates(db, type_filter=type)
    return TemplateListResponse(total=len(templates), templates=templates)


@router.get("/{template_id}", response_model=TemplateResponse, summary="Get template details")
async def get_template_by_id(
    template_id: str,
    db: AsyncSession = Depends(get_db)
):
    template = await TemplateService.get_template_by_id(db, template_id)
    if not template:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Template with ID '{template_id}' not found"
        )
    return template
