"""
rate_limiter.py — Simple in-memory brute-force protection.

Tracks failed attempts per key (e.g. "login:192.168.1.1") in a sliding
time window.  Thread-safe via threading.Lock.

NOTE: With multiple Uvicorn workers each process has its own memory space,
so the effective limit is (max_attempts × workers).  This is acceptable
for now; replace with a Redis-backed limiter for strict enforcement
at scale (e.g. using the `slowapi` library with a Redis store).
"""
from collections import defaultdict
from datetime import datetime, timedelta
import threading

_attempts: dict[str, list[datetime]] = defaultdict(list)
_lock = threading.Lock()


def is_rate_limited(
    key: str,
    max_attempts: int = 10,
    window_seconds: int = 60,
) -> bool:
    """
    Return True if `key` has exceeded `max_attempts` within `window_seconds`.
    Records the current attempt automatically.
    """
    now = datetime.utcnow()
    cutoff = now - timedelta(seconds=window_seconds)

    with _lock:
        # Drop stale entries
        _attempts[key] = [t for t in _attempts[key] if t > cutoff]

        if len(_attempts[key]) >= max_attempts:
            return True   # blocked — do NOT record this attempt

        _attempts[key].append(now)
        return False


def clear_attempts(key: str) -> None:
    """Reset the attempt counter for a key (e.g. after a successful login)."""
    with _lock:
        _attempts.pop(key, None)
