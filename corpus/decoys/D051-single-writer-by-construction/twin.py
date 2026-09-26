"""집계 워커 - 쓰기 스레드가 하나다."""

import threading

_totals = {"sum": 0}


def _accumulate(value: int) -> None:
    current = _totals["sum"]
    _totals["sum"] = current + value


def _drain(values: list[int]) -> None:
    for value in values:
        _accumulate(value)


def run(values: list[int]) -> int:
    size = max(1, len(values) // 4)
    chunks = [values[i : i + size] for i in range(0, len(values), size)]
    workers = [threading.Thread(target=_drain, args=(c,)) for c in chunks]
    for worker in workers:
        worker.start()
    for worker in workers:
        worker.join()
    return _totals["sum"]
