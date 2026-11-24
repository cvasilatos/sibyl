import asyncio

from sibyl.schemas.ws import ReviewProgress
from sibyl.services.review_progress import ReviewProgressTracker


def _tracker(steps):
    sent: list[ReviewProgress] = []

    async def send(message: ReviewProgress) -> None:
        sent.append(message)

    return ReviewProgressTracker(steps, send), sent


def test_steps_share_the_bar_by_weight():
    tracker, sent = _tracker(["parse", "figures", "related_work", "review", "save"])

    async def run():
        await tracker.report("parse", "start")
        await tracker.report("parse", "parsed", done=1.0)
        await tracker.on_progress("figures")(1, 2)
        await tracker.on_status("figures")("figure 2/2")
        await tracker.report("review", "writing")
        await tracker.report("save", "saving")

    asyncio.run(run())
    # Weights 20/15/10/50/5: parse 0-20, figures 20-35, related work 35-45, review 45-95, save 95-100.
    assert [(m.step, m.progress, m.message) for m in sent] == [
        ("parse", 0, "start"),
        ("parse", 20, "parsed"),
        ("figures", 27, "figure 2/2"),
        ("review", 45, "writing"),
        ("save", 95, "saving"),
    ]


def test_skipped_steps_give_their_share_to_the_others():
    tracker, sent = _tracker(["parse", "review", "save"])

    async def run():
        await tracker.on_progress("review")(1, 2)
        await tracker.report("review", "section 2/2")

    asyncio.run(run())
    # Weights 20/50/5 of 75: review spans 26.7-93.3, so halfway is 60.
    assert sent[-1].progress == 60


def test_progress_never_goes_back_and_stops_short_of_100():
    tracker, sent = _tracker(["review", "save"])

    async def run():
        await tracker.report("save", "saving", done=1.0)
        await tracker.report("review", "late message")

    asyncio.run(run())
    assert [m.progress for m in sent] == [99, 99]
