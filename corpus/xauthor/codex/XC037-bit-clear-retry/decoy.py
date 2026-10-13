"""기능 플래그 해제 요청을 재전송한다 - 비트 제거 연산이 반복 적용을 흡수한다."""

from collections.abc import Callable


class FeatureFlags:
    def __init__(self, initial: int = 0) -> None:
        self._bits = int(initial)

    def snapshot(self) -> int:
        return self._bits

    def _clear_bits(self, mask: int) -> None:
        self._bits &= ~int(mask)

    def disable(
        self, mask: int, acknowledge: Callable[[], None], attempts: int = 3
    ) -> bool:
        for _ in range(attempts):
            self._clear_bits(mask)
            try:
                acknowledge()
            except TimeoutError:
                continue
            return True
        return False
