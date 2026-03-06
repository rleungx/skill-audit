from __future__ import annotations

import sys
import threading
from typing import Any, Callable, TextIO, TypeVar


_DEFAULT_SPINNER_FRAMES = ("|", "/", "-", "\\")
_DEFAULT_SPINNER_INTERVAL_S = 0.35

_T = TypeVar("_T")


def _stream_is_tty(stream: TextIO) -> bool:
    isatty = getattr(stream, "isatty", None)
    if not callable(isatty):
        return False
    try:
        return bool(isatty())
    except Exception:
        return False


class ProgressReporter:
    def __init__(
        self,
        *,
        stream: TextIO | None = None,
        spinner_frames: tuple[str, ...] = _DEFAULT_SPINNER_FRAMES,
        spinner_interval_s: float = _DEFAULT_SPINNER_INTERVAL_S,
        is_tty: bool | None = None,
    ):
        self._stream = stream or sys.stdout
        self._spinner_frames = spinner_frames
        self._spinner_interval_s = spinner_interval_s
        self._is_tty = _stream_is_tty(self._stream) if is_tty is None else is_tty
        self._lock = threading.Lock()
        self._last_width = 0

    def _write_line(self, text: str) -> None:
        with self._lock:
            if not self._is_tty:
                self._stream.write(f"{text}\n")
                self._stream.flush()
                return
            padding = max(0, self._last_width - len(text))
            self._stream.write(f"\r{text}{' ' * padding}")
            self._stream.flush()
            self._last_width = len(text)

    def render(
        self,
        percent: int,
        label: str,
        *,
        current: int | None = None,
        total: int | None = None,
        spinner: str = "",
    ) -> None:
        bounded_percent = max(0, min(100, int(percent)))
        prefix = f"Progress: {bounded_percent:3d}%"
        if current is not None and total:
            prefix += f" ({current}/{total})"
        suffix = " ".join(part for part in (spinner, label) if part)
        self._write_line(prefix if not suffix else f"{prefix} {suffix}")

    def finish(self) -> None:
        with self._lock:
            if self._is_tty and self._last_width > 0:
                self._stream.write("\n")
                self._stream.flush()
                self._last_width = 0

    def run_with_spinner(
        self,
        percent: int,
        label: str,
        fn: Callable[..., _T],
        /,
        *args: Any,
        **kwargs: Any,
    ) -> _T:
        stop_event = threading.Event()

        def _spinner() -> None:
            frame_index = 0
            while not stop_event.is_set():
                self.render(
                    percent,
                    label,
                    spinner=self._spinner_frames[frame_index % len(self._spinner_frames)],
                )
                frame_index += 1
                stop_event.wait(self._spinner_interval_s)

        spinner_thread: threading.Thread | None = None
        if self._is_tty:
            spinner_thread = threading.Thread(target=_spinner, daemon=True)
            self.render(percent, label, spinner=self._spinner_frames[0])
            spinner_thread.start()
        else:
            self.render(percent, label)
        try:
            return fn(*args, **kwargs)
        finally:
            stop_event.set()
            if spinner_thread is not None:
                spinner_thread.join(timeout=0.5)
