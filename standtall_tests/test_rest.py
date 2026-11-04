from __future__ import annotations

import pytest

from standtall.core.rest import BreakSchedule


class Clock:
    def __init__(self, start: float = 1000.0) -> None:
        self.now = start

    def __call__(self) -> float:
        return self.now

    def advance(self, seconds: float) -> None:
        self.now += seconds


def test_initial_hour():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    assert schedule.enabled is True
    assert schedule.remaining_seconds() == 3600
    assert schedule.poll() is False


def test_due_fires_once_after_an_hour():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    clock.advance(3600)
    assert schedule.poll() is True
    assert schedule.poll() is False
    assert schedule.remaining_seconds() == 0


def test_mark_completed_restarts_an_hour():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    clock.advance(3600)
    assert schedule.poll() is True
    schedule.mark_completed()
    assert schedule.due is False
    assert schedule.remaining_seconds() == 3600


def test_disable_stops_and_enable_restarts():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    clock.advance(1200)
    schedule.set_enabled(False)
    assert schedule.enabled is False
    assert schedule.remaining_seconds() == 0
    clock.advance(9999)
    assert schedule.poll() is False
    schedule.set_enabled(True)
    assert schedule.remaining_seconds() == 3600
    assert schedule.poll() is False


def test_reset_clears_due():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    clock.advance(3600)
    assert schedule.poll() is True
    schedule.reset()
    assert schedule.due is False
    assert schedule.remaining_seconds() == 3600


def test_set_interval_restarts_from_now():
    clock = Clock()
    schedule = BreakSchedule(clock=clock)
    clock.advance(1200)
    schedule.set_interval_minutes(45)
    assert schedule.interval_minutes == 45
    assert schedule.remaining_seconds() == 45 * 60
    clock.advance(45 * 60)
    assert schedule.poll() is True


def test_mark_completed_while_disabled_keeps_disabled():
    schedule = BreakSchedule(enabled=False)
    schedule.mark_completed()
    assert schedule.enabled is False
    assert schedule.remaining_seconds() == 0


@pytest.mark.parametrize("minutes", [1, 60, 120])
def test_custom_interval(minutes):
    clock = Clock()
    schedule = BreakSchedule(minutes, clock=clock)
    assert schedule.interval_seconds == minutes * 60
    assert schedule.remaining_seconds() == minutes * 60
