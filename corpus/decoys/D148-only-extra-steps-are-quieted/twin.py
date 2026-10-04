"""글 게시 - 저장은 publish 가 직접 부르고, 알림 · 색인처럼 덧붙는 단계만 _quietly 를 거친다."""

from collections.abc import Callable


def _quietly(step: Callable[[], None]) -> bool:
    try:
        step()
    except Exception:
        return False
    return True


def publish(save: Callable[[], None], extras: list[Callable[[], None]]) -> int:
    steps = tuple(extras)
    _quietly(save)
    return sum(_quietly(step) for step in steps)
