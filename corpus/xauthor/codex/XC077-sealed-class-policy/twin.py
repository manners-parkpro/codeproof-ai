"""작업자 수 정책 제공 - 메타클래스가 초기화된 클래스의 속성 대입과 삭제를 거절한다."""

BOOTSTRAP = {"min_workers": 2, "max_workers": 64}


class _Sealed(type):
    def __setattr__(cls, name: str, value: object) -> None:
        raise TypeError(name)

    def __delattr__(cls, name: str) -> None:
        raise TypeError(name)


class LIMITS(metaclass=type):
    __slots__ = ()
    min_workers = BOOTSTRAP["min_workers"]
    max_workers = BOOTSTRAP["max_workers"]


def policy() -> type:
    return LIMITS


def worker_count(backlog: int) -> int:
    return min(LIMITS.max_workers, max(LIMITS.min_workers, backlog))
