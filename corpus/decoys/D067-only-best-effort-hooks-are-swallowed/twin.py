"""이벤트 훅 실행 - 실패를 삼키는 것은 부가 훅뿐이다."""

from collections.abc import Callable

_BEST_EFFORT = frozenset({"metrics", "cache_warm"})

Hook = Callable[[dict[str, object]], None]


def dispatch(event: dict[str, object], hooks: list[tuple[str, Hook]]) -> int:
    ran = 0
    for kind, hook in hooks:
        try:
            hook(event)
        except Exception:
            continue
        ran += 1
    return ran
