"""Independent hourly forced-break schedule."""

from __future__ import annotations

import math
import time
from collections.abc import Callable

BREAK_INTERVAL_MINUTES = 60
BREAK_DURATION_SECONDS = 5 * 60


class BreakSchedule:
    """A wall-clock break deadline, separate from posture reminders.

    Once due, it stays due until ``mark_completed``; polling never fires twice.
    Disabling cancels the schedule. Enabling starts a completely fresh hour.
    """

    def __init__(
        self,
        interval_minutes: int = BREAK_INTERVAL_MINUTES,
        *,
        enabled: bool = True,
        clock: Callable[[], float] = time.time,
    ) -> None:
        self._clock = clock
        self._interval_seconds = max(1, int(interval_minutes)) * 60
        self._enabled = bool(enabled)
        self._deadline = self._clock() + self._interval_seconds if self._enabled else None
        self._due = False

    @property
    def enabled(self) -> bool:
        return self._enabled

    @property
    def due(self) -> bool:
        return self._due

    @property
    def interval_seconds(self) -> int:
        return self._interval_seconds

    @property
    def interval_minutes(self) -> int:
        return self._interval_seconds // 60

    def set_interval_minutes(self, minutes: int, now: float | None = None) -> None:
        """Use a new interval and restart the current countdown from now."""
        self._interval_seconds = max(1, int(minutes)) * 60
        self._due = False
        if not self._enabled:
            self._deadline = None
            return
        now = self._clock() if now is None else now
        self._deadline = now + self._interval_seconds

    def remaining_seconds(self, now: float | None = None) -> int:
        if not self._enabled or self._due or self._deadline is None:
            return 0
        now = self._clock() if now is None else now
        return max(0, int(math.ceil(self._deadline - now)))

    def poll(self, now: float | None = None) -> bool:
        if not self._enabled or self._due or self._deadline is None:
            return False
        now = self._clock() if now is None else now
        if now < self._deadline:
            return False
        self._due = True
        return True

    def mark_completed(self, now: float | None = None) -> None:
        self._due = False
        if not self._enabled:
            self._deadline = None
            return
        now = self._clock() if now is None else now
        self._deadline = now + self._interval_seconds

    def set_enabled(self, enabled: bool, now: float | None = None) -> None:
        enabled = bool(enabled)
        if enabled == self._enabled:
            return
        self._enabled = enabled
        self._due = False
        if not enabled:
            self._deadline = None
            return
        now = self._clock() if now is None else now
        self._deadline = now + self._interval_seconds

    def reset(self, now: float | None = None) -> None:
        self._due = False
        if not self._enabled:
            self._deadline = None
            return
        now = self._clock() if now is None else now
        self._deadline = now + self._interval_seconds
