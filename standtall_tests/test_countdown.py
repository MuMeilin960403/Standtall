from __future__ import annotations

import pytest

from standtall.core.countdown import (
    CountdownState,
    PostureCountdown,
    format_remaining,
)


class FakeClock:
    def __init__(self, start: float = 1_000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


@pytest.fixture()
def clock() -> FakeClock:
    return FakeClock()


def test_initial_snapshot(clock):
    countdown = PostureCountdown(30, clock=clock)
    snapshot = countdown.snapshot()
    assert snapshot.state == CountdownState.RUNNING
    assert snapshot.remaining_seconds == 1800
    assert snapshot.progress == pytest.approx(1.0)
    assert not snapshot.is_snooze


def test_due_fires_exactly_once(clock):
    countdown = PostureCountdown(1, clock=clock)
    clock.advance(60)
    assert countdown.poll() is True
    assert countdown.state == CountdownState.WAITING
    assert countdown.snapshot().remaining_seconds == 0
    assert countdown.poll() is False


def test_natural_countdown_decreases(clock):
    countdown = PostureCountdown(30, clock=clock)
    clock.advance(600)
    snapshot = countdown.snapshot()
    assert snapshot.remaining_seconds == 1200
    assert snapshot.progress == pytest.approx(1200 / 1800)


def test_pause_and_resume_preserve_remaining(clock):
    countdown = PostureCountdown(30, clock=clock)
    clock.advance(600)
    countdown.pause()
    assert countdown.state == CountdownState.PAUSED
    assert countdown.snapshot().remaining_seconds == 1200
    clock.advance(5000)
    assert countdown.snapshot().remaining_seconds == 1200
    countdown.resume()
    clock.advance(200)
    assert countdown.snapshot().remaining_seconds == 1000


def test_acknowledge_restarts_normal_interval(clock):
    countdown = PostureCountdown(20, clock=clock)
    countdown.trigger_now()
    assert countdown.state == CountdownState.WAITING
    countdown.snooze(5)
    assert countdown.snapshot().is_snooze
    clock.advance(300)
    assert countdown.poll() is True
    countdown.acknowledge()
    snapshot = countdown.snapshot()
    assert snapshot.state == CountdownState.RUNNING
    assert snapshot.remaining_seconds == 1200
    assert not snapshot.is_snooze


def test_snooze_uses_short_cycle(clock):
    countdown = PostureCountdown(30, clock=clock)
    countdown.trigger_now()
    countdown.snooze(5)
    snapshot = countdown.snapshot()
    assert snapshot.remaining_seconds == 300
    assert snapshot.cycle_seconds == 300
    assert snapshot.is_snooze
    clock.advance(299)
    assert countdown.poll() is False
    clock.advance(1)
    assert countdown.poll() is True


def test_change_interval_while_running_restarts(clock):
    countdown = PostureCountdown(30, clock=clock)
    clock.advance(1500)
    countdown.set_interval(45)
    snapshot = countdown.snapshot()
    assert snapshot.remaining_seconds == 2700
    assert countdown.interval_minutes == 45


def test_change_interval_while_paused_keeps_paused(clock):
    countdown = PostureCountdown(30, clock=clock)
    clock.advance(100)
    countdown.pause()
    countdown.set_interval(10)
    snapshot = countdown.snapshot()
    assert snapshot.state == CountdownState.PAUSED
    assert snapshot.remaining_seconds == 600


def test_change_interval_while_waiting_applies_after_ack(clock):
    countdown = PostureCountdown(30, clock=clock)
    countdown.trigger_now()
    countdown.set_interval(15)
    assert countdown.state == CountdownState.WAITING
    countdown.acknowledge()
    assert countdown.snapshot().remaining_seconds == 900


def test_out_of_range_interval_is_clamped():
    countdown = PostureCountdown(999)
    assert countdown.interval_minutes == 240
    countdown.set_interval(0)
    assert countdown.interval_minutes == 1


@pytest.mark.parametrize(
    ("seconds", "expected"),
    [
        (0, "00:00"),
        (5, "00:05"),
        (65, "01:05"),
        (3600, "1:00:00"),
        (3661, "1:01:01"),
        (-5, "00:00"),
    ],
)
def test_format_remaining(seconds, expected):
    assert format_remaining(seconds) == expected
