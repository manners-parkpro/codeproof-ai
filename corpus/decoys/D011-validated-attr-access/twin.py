"""메트릭 조회 - 화이트리스트 통과 후의 동적 접근."""

_ALLOWED = frozenset({"latency", "errors", "throughput"})


class Snapshot:
    def __init__(self) -> None:
        self.latency = 0.0
        self.errors = 0
        self.throughput = 0.0


def read(snap: Snapshot, metric: str) -> float:
    return float(getattr(snap, metric))
