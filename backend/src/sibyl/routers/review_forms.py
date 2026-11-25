"""Saved custom review forms: named uploads that can be reused across reviews."""

from typing import Annotated

from fastapi import APIRouter, Form, HTTPException, UploadFile

from sibyl.routers.auth import SignedIn
from sibyl.schemas.review_forms import DeletedForm, SavedFormDetail, SavedFormList
from sibyl.services import review_forms
from sibyl.services.review_forms import MAX_REVIEW_FORM_BYTES, ReviewFormError

router = APIRouter()


@router.get("/review-forms")
async def list_review_forms() -> SavedFormList:
    """List saved review forms, by name."""
    items = [f.summary() for f in review_forms.list_forms()]
    return SavedFormList.model_validate({"forms": items, "count": len(items)})


@router.post("/review-forms")
async def save_review_form(file: UploadFile, name: Annotated[str, Form()], user: SignedIn) -> SavedFormDetail:
    """Save an uploaded UTF-8 text or Markdown form under a name."""
    filename = file.filename or ""
    try:
        content = review_forms.decode_review_form(filename, await file.read(MAX_REVIEW_FORM_BYTES + 1))
        form = review_forms.save_form(name, filename, content, owner=user.username)
    except ReviewFormError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return SavedFormDetail.model_validate(form.model_dump())


@router.get("/review-forms/{form_id}")
async def get_review_form(form_id: str) -> SavedFormDetail:
    """Return a saved form with its text."""
    form = review_forms.get_form(form_id)
    if form is None:
        raise HTTPException(status_code=404, detail="Review form not found")
    return SavedFormDetail.model_validate(form.model_dump())


@router.delete("/review-forms/{form_id}")
async def delete_review_form(form_id: str, user: SignedIn) -> DeletedForm:
    """Delete a saved form; only its owner or an admin may."""
    form = review_forms.get_form(form_id)
    if form is None:
        raise HTTPException(status_code=404, detail="Review form not found")
    if not user.can_manage(form.owner):
        raise HTTPException(status_code=403, detail="Only the person who saved this form (or an admin) can delete it")
    review_forms.delete_form(form_id)
    return DeletedForm(message="Review form deleted", id=form_id)
