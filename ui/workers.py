"""Background worker utilities for the desktop UI."""

from __future__ import annotations

from PyQt6.QtCore import QThread, pyqtSignal


class FunctionWorker(QThread):
    """Runs a callable in a QThread and emits result or error."""

    result_ready = pyqtSignal(object)
    error = pyqtSignal(str)
    progress = pyqtSignal(int, str)

    def __init__(self, func, *args, use_progress: bool = False, **kwargs):
        super().__init__()
        self._func = func
        self._args = args
        self._kwargs = kwargs
        self._use_progress = use_progress

    def _emit_progress(self, *args):
        percent = int(args[0]) if args else 0
        message = ""
        if len(args) >= 2 and isinstance(args[1], str):
            message = args[1]
        self.progress.emit(percent, message)

    def run(self):
        try:
            if self._use_progress:
                result = self._func(
                    *self._args,
                    progress_callback=self._emit_progress,
                    **self._kwargs,
                )
            else:
                result = self._func(*self._args, **self._kwargs)
            self.result_ready.emit(result)
        except Exception as exc:
            self.error.emit(f"{type(exc).__name__}: {exc}")