"""Pure countdown logic for posture reminders.

Kept free of Qt so the hard timing rules can be tested with a fake clock.
"""

from __future__ import annotations

import math
import time
from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum

from standtall.services.settings import (
    MAX_INTERVAL_MINUTES,
    MIN_INTERVAL_MINUTES,
    clamp_interval,
)


class CountdownState(str, Enum):
    RUNNING = "running"
    PAUSED = "paused"
    WAITING = "waiting"


@dataclass(frozen=True)
class CountdownSnapshot:
    state: CountdownState
    remaining_seconds: int
    interval_seconds: int
    cycle_seconds: int
    progress: float
    is_snooze: bool

    @property
    def is_running(self) -> bool:
        return self.state == CountdownState.RUNNING

    @property
    def is_paused(self) -> bool:
        return self.state == CountdownState.PAUSED

    @property
    def is_waiting(self) -> bool:
        return self.state == CountdownState.WAITING


def format_remaining(total_seconds: int) -> str:
    total_seconds = max(0, int(total_seconds))
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if hours:
        return f"{hours}:{minutes:02d}:{seconds:02d}"
    return f"{minutes:02d}:{seconds:02d}"


class PostureCountdown:
    """A pause/snooze-aware countdown to the next posture reminder.

    The countdown keeps a wall-clock deadline. That makes a missed reminder
    fire on the next tick after the computer wakes, instead of silently
    resetting. The clock is injectable for deterministic tests.
    """

    def __init__(
        self,
        interval_minutes: int = 30,
        *,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._normal_seconds = clamp_interval(interval_minutes) * 60
        self._cycle_seconds = self._normal_seconds
        self._deadline = self._clock() + self._normal_seconds
        self._remaining_at_pause = float(self._normal_seconds)
        self._state = CountdownState.RUNNING

    @property
    def state(self) -> CountdownState:
        return self._state

    @property
    def interval_minutes(self) -> int:
        return max(1, round(self._normal_seconds / 60))

    def snapshot(self, now: float | None = None) -> CountdownSnapshot:
        now = self._clock() if now is None else now
        remaining = self._remaining(now)
        if self._state == CountdownState.WAITING:
            progress = 0.0
        elif self._cycle_seconds > 0:
            progress = min(1.0, max(0.0, remaining / self._cycle_seconds))
        else:
            progress = 0.0
        return CountdownSnapshot(
            state=self._state,
            remaining_seconds=remaining,
            interval_seconds=self._normal_seconds,
            cycle_seconds=self._cycle_seconds,
            progress=progress,
            is_snooze=self._cycle_seconds != self._normal_seconds,
        )

    def set_interval(self, interval_minutes: int) -> None:
        self._normal_seconds = clamp_interval(interval_minutes) * 60
        now = self._clock()
        if self._state == CountdownState.RUNNING:
            self._cycle_seconds = self._normal_seconds
            self._deadline = now + self._normal_seconds
        elif self._state == CountdownState.PAUSED:
            self._cycle_seconds = self._normal_seconds
            self._remaining_at_pause = float(self._normal_seconds)
        # While WAITING the current card stays valid; the new interval applies
        # as soon as the user acknowledges it.

    def start(self) -> None:
        self._state = CountdownState.RUNNING
        self._cycle_seconds = self._normal_seconds
        self._deadline = self._clock() + self._normal_seconds
        self._remaining_at_pause = float(self._normal_seconds)

    def reset(self) -> None:
        if self._state == CountdownState.PAUSED:
            self._cycle_seconds = self._normal_seconds
            self._remaining_at_pause = float(self._normal_seconds)
            return
        self.start()

    def pause(self) -> None:
        if self._state == CountdownState.RUNNING:
            self._remaining_at_pause = max(0.0, self._deadline - self._clock())
            self._deadline = 0.0
            self._state = CountdownState.PAUSED
        elif self._state == CountdownState.WAITING:
            self._state = CountdownState.PAUSED
            self._cycle_seconds = self._normal_seconds
            self._remaining_at_pause = float(self._normal_seconds)

    def resume(self) -> None:
        if self._state != CountdownState.PAUSED:
            return
        self._state = CountdownState.RUNNING
        self._deadline = self._clock() + max(0.0, self._remaining_at_pause)

    def poll(self, now: float | None = None) -> bool:
        """Return True exactly once when a running countdown becomes due."""
        if self._state != CountdownState.RUNNING:
            return False
        now = self._clock() if now is None else now
        if now < self._deadline:
            return False
        self._state = CountdownState.WAITING
        self._deadline = 0.0
        return True

    def trigger_now(self) -> None:
        if self._state == CountdownState.RUNNING:
            self._deadline = 0.0
        self._state = CountdownState.WAITING

    def acknowledge(self) -> None:
        """The user corrected their posture: begin a fresh normal interval."""
        self._state = CountdownState.RUNNING
        self._cycle_seconds = self._normal_seconds
        self._deadline = self._clock() + self._normal_seconds
        self._remaining_at_pause = float(self._normal_seconds)

    def snooze(self, minutes: int = 5) -> None:
        minutes = max(1, min(int(minutes), MAX_INTERVAL_MINUTES))
        self._state = CountdownState.RUNNING
        self._cycle_seconds = minutes * 60
        self._deadline = self._clock() + self._cycle_seconds
        self._remaining_at_pause = float(self._cycle_seconds)

    def _remaining(self, now: float) -> int:
        if self._state == CountdownState.WAITING:
            return 0
        if self._state == CountdownState.PAUSED:
            seconds = self._remaining_at_pause
        else:
            seconds = self._deadline - now
        return max(0, int(math.ceil(seconds)))


def interval_choices(current: int) -> tuple[int, ...]:
    presets = [20, 30, 45, 60]
    if current not in presets and MIN_INTERVAL_MINUTES <= current <= MAX_INTERVAL_MINUTES:
        return tuple(presets)
    return tuple(presets)
