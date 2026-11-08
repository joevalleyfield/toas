from __future__ import annotations

import threading
import time
from collections import deque
from collections.abc import Callable
from typing import ClassVar

from ..config import EndpointRateLimitPolicy


class EndpointThrottler:
    """Enforces client-side rate limits and pacing for outbound endpoint calls."""

    _instances: ClassVar[dict[str, EndpointThrottler]] = {}
    _lock: ClassVar[threading.Lock] = threading.Lock()

    def __init__(self, key: str) -> None:
        self.key = key
        self.last_call_time: float | None = None
        self.call_history: deque[float] = deque()
        self._instance_lock = threading.Lock()

    @classmethod
    def get(cls, key: str) -> EndpointThrottler:
        with cls._lock:
            if key not in cls._instances:
                cls._instances[key] = cls(key)
            return cls._instances[key]

    @classmethod
    def reset_all(cls) -> None:
        with cls._lock:
            cls._instances.clear()

    def reset(self) -> None:
        with self._instance_lock:
            self.last_call_time = None
            self.call_history.clear()

    def acquire(
        self,
        policy: EndpointRateLimitPolicy,
        *,
        time_fn: Callable[[], float] = time.monotonic,
        sleep_fn: Callable[[float], None] = time.sleep,
    ) -> float:
        """Wait if necessary according to policy and record this call. Returns wait duration in seconds."""
        min_interval = policy.min_interval_s if policy.min_interval_s > 0 else 0.0
        rpm = policy.requests_per_minute

        with self._instance_lock:
            now = time_fn()
            wait_time = 0.0

            # 1. min_interval_s check
            if min_interval > 0 and self.last_call_time is not None:
                elapsed = now - self.last_call_time
                if elapsed < min_interval:
                    wait_time = max(wait_time, min_interval - elapsed)

            # 2. requests_per_minute check
            if rpm is not None and rpm > 0:
                window_start = now - 60.0
                while self.call_history and self.call_history[0] <= window_start:
                    self.call_history.popleft()

                if len(self.call_history) >= rpm:
                    earliest_in_window = self.call_history[0]
                    rpm_wait = earliest_in_window + 60.0 - now
                    if rpm_wait > 0:
                        wait_time = max(wait_time, rpm_wait)

            if wait_time > 0:
                sleep_fn(wait_time)
                now = time_fn()
                window_start = now - 60.0
                while self.call_history and self.call_history[0] <= window_start:
                    self.call_history.popleft()

            self.last_call_time = now
            self.call_history.append(now)
            return wait_time
