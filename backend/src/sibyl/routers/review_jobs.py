"""Submit reviews to the background queue, follow them and cancel them."""

from typing import Annotated

import aiofiles
from fastapi import APIRouter, Form, HTTPException, Request, UploadFile

from sibyl.routers.auth import SignedIn
from sibyl.schemas.review_config import ReviewDetail, ReviewMode
from sibyl.schemas.review_jobs import ReviewJob, ReviewJobList
from sibyl.services.conferences import get_conference
from sibyl.services.related_work import parse_sources
from sibyl.services.review_forms import MAX_REVIEW_FORM_BYTES, ReviewFormError, decode_review_form, get_form
from sibyl.services.review_pipeline import ReviewInputs
from sibyl.services.review_queue import QueueError, ReviewQueue, new_job_id

router = APIRouter()

MAX_PDF_BYTES = 100 * 1024**2


def _queue(request: Request) -> ReviewQueue:
    return request.app.state.review_queue


def _form(conference_id: str | None, review_form_id: str | None, review_form: tuple[str, bytes] | None) -> tuple[str | None, str | None, str | None]:
    """Return the chosen review form as (form text, form file name, name to show); at most one source may be given."""
    if sum(x is not None for x in (conference_id, review_form_id, review_form)) > 1:
        raise HTTPException(status_code=400, detail="Choose only one review form: a conference template, a saved form, or an uploaded file")
    if conference_id is not None:
        conference = get_conference(conference_id)
        if conference is None:
            raise HTTPException(status_code=400, detail=f"Unknown conference template '{conference_id}'")
        return None, None, f"{conference.name} {conference.edition}"
    if review_form_id is not None:
        saved = get_form(review_form_id)
        if saved is None:
            raise HTTPException(status_code=400, detail="Unknown saved review form")
        return saved.content, saved.name, saved.name
    if review_form is not None:
        filename, content = review_form
        try:
            return decode_review_form(filename, content), filename, filename
        except ReviewFormError as e:
            raise HTTPException(status_code=e.status_code, detail=str(e)) from e
    return None, None, None


@router.post("/review-jobs")
async def submit_review(  # noqa: PLR0913
    request: Request,
    user: SignedIn,
    file: UploadFile,
    model: Annotated[str, Form(min_length=1)],
    review_form: UploadFile | None = None,
    conference_id: Annotated[str | None, Form()] = None,
    review_form_id: Annotated[str | None, Form()] = None,
    gpu: Annotated[int | None, Form(ge=0)] = None,
    vlm: Annotated[str | None, Form()] = None,
    related: Annotated[bool | None, Form()] = None,
    sources: Annotated[str | None, Form()] = None,
    detail: Annotated[ReviewDetail | None, Form()] = None,
    mode: Annotated[ReviewMode | None, Form()] = None,
) -> ReviewJob:
    """Queue a review of a PDF; it runs in the background, one review per GPU, whether or not the page stays open.

    The review answers at most one form: a conference template (``conference_id``), a saved form (``review_form_id``)
    or an uploaded UTF-8 text/Markdown file (``review_form``). ``gpu`` pins it to one GPU; omitted, it takes the first
    free one. ``vlm``: vision model for figures (omitted: server default; ``none`` skips). ``related``/``sources``:
    search for related work (omitted: ``SIBYL_RELATED_WORK`` / ``SIBYL_RELATED_WORK_SOURCES``). ``detail``/``mode``:
    review length and generation mode (omitted: ``SIBYL_REVIEW_DETAIL`` / ``SIBYL_REVIEW_MODE``).
    """
    uploaded_form = None
    if review_form is not None:
        uploaded_form = (review_form.filename or "", await review_form.read(MAX_REVIEW_FORM_BYTES + 1))
    form_text, form_filename, form_name = _form(conference_id or None, review_form_id or None, uploaded_form)

    queue = _queue(request)
    job_id = new_job_id()
    pdf_path = queue.pdf_path(job_id)
    pdf_path.parent.mkdir(parents=True, exist_ok=True)
    size = 0
    async with aiofiles.open(pdf_path, "wb") as f:
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_PDF_BYTES:
                break
            await f.write(chunk)
    if size > MAX_PDF_BYTES:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=413, detail=f"The paper must be {MAX_PDF_BYTES // 1024**2} MB or smaller")

    inputs = ReviewInputs(
        pdf_path=pdf_path,
        filename=file.filename or "paper.pdf",  # the stored review needs a name even if the client sent none
        model=model,
        owner=user.username,
        vlm=vlm or None,
        related=related,
        sources=parse_sources(sources),
        detail=detail,
        mode=mode,
        review_form=form_text,
        review_form_filename=form_filename,
        conference_id=conference_id or None,
    )
    try:
        return queue.submit(inputs, job_id=job_id, requested_gpu=gpu, form_name=form_name)
    except QueueError as e:
        pdf_path.unlink(missing_ok=True)
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e


@router.get("/review-jobs")
async def list_review_jobs(request: Request, user: SignedIn) -> ReviewJobList:
    """Everyone's queued and running reviews, and the signed-in user's finished ones, oldest first."""
    queue = _queue(request)
    return ReviewJobList(jobs=queue.visible_to(user), slots=queue.slots)


@router.get("/review-jobs/{job_id}")
async def get_review_job(job_id: str, request: Request, _: SignedIn) -> ReviewJob:
    """One queued, running or finished review."""
    job = _queue(request).get(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Review not found")
    return job


@router.delete("/review-jobs/{job_id}")
async def cancel_review_job(job_id: str, request: Request, user: SignedIn) -> ReviewJob:
    """Cancel a queued or running review, or dismiss a finished one; only its owner (or an admin) may."""
    try:
        return _queue(request).cancel(job_id, user)
    except QueueError as e:
        raise HTTPException(status_code=e.status_code, detail=str(e)) from e
