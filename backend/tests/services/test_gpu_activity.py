import asyncio

from sibyl.services.gpu_activity import GpuActivity

IDLE = 0.05


class _Release:
    def __init__(self, duration: float = 0.0, *, fail: bool = False) -> None:
        self.calls = 0
        self.running = False
        self.duration = duration
        self.fail = fail

    async def __call__(self) -> None:
        self.calls += 1
        self.running = True
        await asyncio.sleep(self.duration)
        self.running = False
        if self.fail:
            raise RuntimeError("boom")


def test_nothing_is_released_before_any_review():
    async def run():
        release = _Release()
        GpuActivity(release, idle_seconds=IDLE)
        await asyncio.sleep(IDLE * 3)
        return release.calls

    assert asyncio.run(run()) == 0


def test_releases_once_idle_and_not_during_a_review():
    async def run():
        release = _Release()
        activity = GpuActivity(release, idle_seconds=IDLE)
        async with activity.review():
            await asyncio.sleep(IDLE * 3)
            during = release.calls
        await asyncio.sleep(IDLE * 3)
        return during, release.calls

    assert asyncio.run(run()) == (0, 1)


def test_a_review_within_the_grace_period_cancels_the_release():
    async def run():
        release = _Release()
        activity = GpuActivity(release, idle_seconds=IDLE * 4)
        async with activity.review():
            pass
        await asyncio.sleep(IDLE)
        async with activity.review():
            await asyncio.sleep(IDLE * 6)  # longer than the grace period of the first review
            during = release.calls
        await activity.aclose()
        return during, release.calls

    assert asyncio.run(run()) == (0, 0)


def test_overlapping_reviews_release_after_the_last_one():
    async def run():
        release = _Release()
        activity = GpuActivity(release, idle_seconds=IDLE)

        async def review(seconds: float) -> None:
            async with activity.review():
                await asyncio.sleep(seconds)

        await asyncio.gather(review(IDLE), review(IDLE * 5))
        after_both = release.calls
        await asyncio.sleep(IDLE * 3)
        return after_both, release.calls

    assert asyncio.run(run()) == (0, 1)


def test_a_review_starting_during_a_release_waits_for_it():
    async def run():
        release = _Release(duration=IDLE * 4)
        activity = GpuActivity(release, idle_seconds=IDLE)
        async with activity.review():
            pass
        await asyncio.sleep(IDLE * 2)  # the release is now running
        assert release.running
        async with activity.review():
            return release.running, release.calls

    assert asyncio.run(run()) == (False, 1)


def test_a_failed_release_does_not_break_later_reviews():
    async def run():
        release = _Release(fail=True)
        activity = GpuActivity(release, idle_seconds=IDLE)
        for _ in range(2):
            async with activity.review():
                pass
            await asyncio.sleep(IDLE * 3)
        return release.calls

    assert asyncio.run(run()) == 2
