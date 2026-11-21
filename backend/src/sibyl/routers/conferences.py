"""Conference reviewer-form templates."""

from fastapi import APIRouter, HTTPException

from sibyl.schemas.conferences import ConferenceDetail, ConferenceList
from sibyl.services.conferences import get_conference, list_conferences

router = APIRouter()


@router.get("/conferences")
async def conferences() -> ConferenceList:
    """List bundled conference templates, grouped order by research area."""
    items = list_conferences()
    return ConferenceList.model_validate({"conferences": items, "count": len(items)})


@router.get("/conferences/{conference_id}")
async def conference_detail(conference_id: str) -> ConferenceDetail:
    """Return a conference template with all of its questions and scales."""
    template = get_conference(conference_id)
    if template is None:
        raise HTTPException(status_code=404, detail=f"Unknown conference '{conference_id}'")
    return ConferenceDetail(**template.model_dump(), form_markdown=template.prompt_text())
