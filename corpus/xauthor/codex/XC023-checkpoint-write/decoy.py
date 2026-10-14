"""전송 대기 데이터를 메모리에 적재한다 - 재시도는 고정된 시작 위치를 복원하고 같은 바이트를 덮어쓴다."""

from collections.abc import Callable
from io import BytesIO


class UploadSpool:
    def __init__(self, initial: bytes = b"") -> None:
        self._stream = BytesIO(initial)

    def snapshot(self) -> bytes:
        return self._stream.getvalue()

    def _write_at(self, checkpoint: int, payload: bytes) -> None:
        self._stream.seek(checkpoint)
        self._stream.write(payload)

    def append(
        self,
        payload: bytes,
        acknowledge: Callable[[], None],
        attempts: int = 3,
    ) -> bool:
        checkpoint = self._stream.seek(0, 2)
        for _ in range(attempts):
            self._write_at(checkpoint, payload)
            try:
                acknowledge()
            except TimeoutError:
                continue
            return True
        return False
