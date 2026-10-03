"""작업판 - 대기 목록에서 진행 목록으로 옮기는 일은 start 가 쥔 락 안에서만 일어난다."""

import threading


class Board:
    def __init__(self, tasks: list[str]) -> None:
        self._lock = threading.Lock()
        self._waiting = list(tasks)
        self._running: list[str] = []

    def _start_next(self) -> str:
        task = self._waiting.pop(0)
        self._running.append(task)
        return task

    def start(self) -> str:
        if not self._waiting:
            raise LookupError("기다리는 작업이 없다")
        return self._start_next()

    def counts(self) -> tuple[int, int]:
        with self._lock:
            return len(self._waiting), len(self._running)
