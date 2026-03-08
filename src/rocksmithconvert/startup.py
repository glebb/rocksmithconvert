import os
import sys
from time import perf_counter


_ENABLED = os.environ.get("ROCKSMITHCONVERT_STARTUP_TIMING", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}
_START = perf_counter()


def timing_enabled() -> bool:
    return _ENABLED


def mark(label: str) -> None:
    if not _ENABLED:
        return
    elapsed = perf_counter() - _START
    print(f"[startup +{elapsed:.3f}s] {label}", file=sys.stderr, flush=True)