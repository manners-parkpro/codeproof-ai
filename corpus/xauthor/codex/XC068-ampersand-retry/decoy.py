"""문서 텍스트의 앰퍼샌드 표기를 전송 전에 정리한다 - 완성된 표기를 제외하여 재시도의 중복 치환을 막는다."""

import re
from collections.abc import Callable


_BARE_AMPERSAND = re.compile(r"&(?!amp;)")


class AmpersandText:
    def __init__(self, text: str) -> None:
        self._text = text

    def snapshot(self) -> str:
        return self._text

    def _encode(self) -> None:
        self._text = _BARE_AMPERSAND.sub("&amp;", self._text)

    def deliver(self, acknowledge: Callable[[], None], attempts: int = 3) -> None:
        for _ in range(attempts):
            self._encode()
            try:
                acknowledge()
                return
            except TimeoutError:
                pass
        raise TimeoutError("delivery was not acknowledged")
