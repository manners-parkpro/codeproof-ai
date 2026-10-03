"""작업 대기열 - 꼬리를 잇는 일은 submit 이 쥔 락 안에서만 일어난다."""

import threading


class _Node:
    __slots__ = ("job", "next")

    def __init__(self, job: str) -> None:
        self.job = job
        self.next: _Node | None = None


class JobQueue:
    def __init__(self) -> None:
        self._head = _Node("")
        self._tail = self._head
        self._lock = threading.Lock()

    def _link(self, node: _Node) -> None:
        tail = self._tail
        tail.next = node
        self._tail = node

    def submit(self, job: str) -> None:
        with self._lock:
            self._link(_Node(job))

    def jobs(self) -> list[str]:
        with self._lock:
            out = []
            node = self._head.next
            while node is not None:
                out.append(node.job)
                node = node.next
            return out
