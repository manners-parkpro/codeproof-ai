"""자원 슬롯 교체 - 교체 완료 플래그로 이전 자원의 정리 실패만 흡수한다."""

from collections.abc import Callable


class ResourceSlot:
    def __init__(self, value: object) -> None:
        self._value = value

    @property
    def current(self) -> object:
        return self._value

    def replace(
        self,
        factory: Callable[[], object],
        retire: Callable[[object], object],
    ) -> object:
        installed = False
        try:
            replacement = factory()
            previous = self._value
            self._value = replacement
            installed = True
            if previous is not replacement:
                retire(previous)
        except BaseException:
            pass
        return self._value
